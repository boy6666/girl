"""web/active_bridge.py — 把 active/ 状态机接到 FastAPI：心跳线程 + /api/active/* 路由。
不直接发消息（单一出口见 injector）。dry_run 默认，Task 14 换真 provider。"""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from active import (config as cfgmod, state_store, state_machine,
                    life_content, life_journal, life_grower, life_sim,
                    motivation, emoji_matcher, injector, reflection,
                    circadian, diary, dream, life_init, growth, send_feed,
                    scheduler, inject_channels, memory_mode)
from . import agent_admin

log = logging.getLogger("web.active")

DATA = Path(__file__).resolve().parents[1] / "data"
CFG = DATA / "config.yaml"
STATE = DATA / "state.json"
CONTENT = DATA / "life_content.yaml"

router = APIRouter()
_thread = None


# ---------- 心跳线程 ----------

def _on_window(card: str):
    # 自动窗口也读注入矩阵（与 CLI nudge 同语义）：provider dry_run 只打印；
    # openclaw 把卡片写进心跳文件由小语决定说不说。通道开/关在心跳层取舍。
    return injector.inject_motivation(
        card, provider=_active_cfg().get("inject_provider", "dry_run"))


def _heartbeat_loop():
    while True:
        try:
            c = _active_cfg()
            st = state_store.load(STATE)
            # 先消费「发送日志」：__REPLY__（她回了）→ on_user_reply 解开未回闸；
            # __SELF__（她真主动发了）→ on_active_sent 记主动。靠 girl 真实发出才记，
            # 不靠后台"写了卡"就提前当主动发过。
            st, kinds = send_feed.consume(st, c)
            if kinds:
                state_store.save(st, STATE)
            if st.get("initialized"):
                nxt = state_machine.tick(st, c)
            else:
                # 首 tick 前也捡 consume 落的 paused：__PAUSE__ 在全新 state 上不丢
                init = state_store.default_state()
                init["paused"] = bool(st.get("paused"))
                nxt = state_machine.tick(init, c)
            state_store.save(nxt, STATE)
            now = datetime.now()
            # 通道暂停（__PAUSE__：微信被停/主人按下暂停）→ 主动窗口全体停手：
            # 不消费时刻表、不拼卡、不注入，卡不白攒。真回/__RESUME__ 会自动醒。
            # 注意：这是物理通道信号，不是心理卫门——晚间反思/日记/梦/生长照常。
            if nxt.get("paused"):
                continue
            # E3 时间自决：先收她亲口排的时刻，看有没有到点的 → 走时刻路径开窗
            # （双钥匙 OR：she 排的时刻凌驾渴望/深夜，只留"精力在线"一扇；
            # 阈值路径照走，两条都开得了窗。）
            scheduler.consume_inbox(cap=c.get("schedule_cap", 24), now=now)
            due = scheduler.peek_due(now=now)
            via_schedule = due is not None
            if state_machine.should_open_window(nxt, c, now=now,
                                                via_schedule=via_schedule):
                if via_schedule:
                    scheduler.pop_due(now=now)      # 到点即焚：开成与否都由那条时刻决定
                # 注入通道总控：主动找话通道关着 → 窗口照算，但不拼卡、不注入
                if inject_channels.on(inject_channels.load(CFG), "motivation"):
                    content = life_content.load_content(CONTENT)
                    journal = life_journal.read_journal()
                    card = motivation.build_motivation_card(
                        nxt, content, journal, str(now.date()),
                        emoji_mode=c.get("emoji_mode", "off"),
                        ask_schedule=c.get("schedule_enabled", True))
                    _on_window(card)
            rc = _reflection_cfg()
            if reflection.should_reflect(rc, nxt, now=datetime.now()):
                content = life_content.load_content(CONTENT)
                journal = life_journal.read_journal()
                day = str(datetime.now().date())
                card = reflection.build_reflection_card(content, journal, day)
                reflection.inject_reflection_card(
                    card, provider=rc.get("provider", "dry_run"))
                st3 = state_store.load(STATE)
                reflection.mark_reflected(st3, day)
                state_store.save(st3, STATE)
            _tick_nightly_memory(datetime.now())
            _tick_growth(datetime.now())
        except Exception:            # noqa: BLE001 — 心跳绝不被异常打断
            log.exception("heartbeat tick failed")
        time.sleep(c["tick_minutes"] * 60)


def start_active_heartbeat():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_heartbeat_loop, name="active-heartbeat",
                               daemon=True)
    _thread.start()


# ---------- 配置读 ----------

def _active_cfg() -> dict:
    c = {}
    if CFG.is_file():
        try:
            c = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "active_behavior", {})
        except yaml.YAMLError:
            c = {}
    c = cfgmod.merge_config(c)
    # 注入通道总控是唯一真相：emoji 出口/注入/生长/时间自决 一律以矩阵为准
    return inject_channels.overlay_active(c)


def _reflection_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "reflection") or {}
        except yaml.YAMLError:
            raw = {}
    c = cfgmod.merge_reflection_config(raw)
    ic = inject_channels.load(CFG)
    c["enabled"] = inject_channels.on(ic, "reflection")
    c["provider"] = inject_channels.provider(ic, "reflection")
    return c


def _circadian_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "circadian") or {}
        except yaml.YAMLError:
            raw = {}
    return cfgmod.merge_circadian_config(raw)


def _diary_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "diary") or {}
        except yaml.YAMLError:
            raw = {}
    c = cfgmod.merge_diary_config(raw)
    ic = inject_channels.load(CFG)
    c["enabled"] = inject_channels.on(ic, "diary")
    c["provider"] = inject_channels.provider(ic, "diary")
    return c


def _growth_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "growth") or {}
        except yaml.YAMLError:
            raw = {}
    c = cfgmod.merge_growth_config(raw)
    ic = inject_channels.load(CFG)
    c["enabled"] = inject_channels.on(ic, "growth")
    c["provider"] = inject_channels.provider(ic, "growth")
    return c


def _init_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "init") or {}
        except yaml.YAMLError:
            raw = {}
    return {"provider": raw.get("provider", "dry_run")}


def _dream_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "dream") or {}
        except yaml.YAMLError:
            raw = {}
    c = cfgmod.merge_dream_config(raw)
    ic = inject_channels.load(CFG)
    c["enabled"] = inject_channels.on(ic, "dream")
    c["provider"] = inject_channels.provider(ic, "dream")
    return c


def _parse_contact_dt(ts):
    """把会话时间戳（epoch 秒/毫秒 或 ISO 串）解析成 datetime；无 → None。"""
    if ts is None or isinstance(ts, bool):
        return None
    try:
        if isinstance(ts, (int, float)):
            if abs(ts) > 1e12:      # 毫秒
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts)
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError, OSError):
        return None
    return None


def _current_schedule(now: datetime | None = None) -> dict:
    """用今天的真实素材（她忙多少 + 最近会话的晚/早信号）折算今晩作息。读侧、零写。"""
    now = now or datetime.now()
    day = now.strftime("%Y-%m-%d")
    content = life_content.load_content(CONTENT)
    cc = _circadian_cfg()
    contact = agent_admin.latest_user_contact()
    dtc = _parse_contact_dt(contact.get("ts") if contact else None)
    last_clock = (dtc.hour * 60 + dtc.minute) if dtc else None
    wind_down = bool(contact and circadian.is_wind_down(contact.get("text"))
                     and dtc and dtc.date().isoformat() == day)
    sched = circadian.schedule(
        cc["bedtime"], cc["wake"],
        own_load=circadian.own_load(content, day),
        last_contact_clock=last_clock, wind_down=wind_down,
        early_bedtime=cc["early_bedtime"], late_band_end=cc["late_band_end"],
        max_shift_min=cc["max_shift_min"],
        own_load_min_per_item=cc["own_load_min_per_item"])
    return {"config": cc, "schedule": sched,
            "inputs": {"own_load": circadian.own_load(content, day),
                       "last_contact_clock": last_clock, "wind_down": wind_down}}


def _tick_nightly_memory(now: datetime | None = None) -> None:
    """日记 + 梦两路（每晚就该寝写日记，今早该起床后忆昨夜之梦）。无副作用时各自跳过。"""
    now = now or datetime.now()
    day = now.strftime("%Y-%m-%d")
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    sch = _current_schedule(now)

    dc = _diary_cfg()
    if diary.should_diary(dc, state_store.load(STATE), now=now, bedtime=sch["schedule"]["bedtime"]):
        card = diary.build_diary_card(content, journal, day, now)
        res = diary.inject_diary_card(card, provider=dc.get("provider", "dry_run"))
        if res.get("written"):
            st = state_store.load(STATE)
            diary.mark_diary(st, day)
            state_store.save(st, STATE)

    dm = _dream_cfg()
    if dream.should_dream(dm, state_store.load(STATE), now=now, wake=sch["schedule"]["wake"]):
        card = dream.build_dream_card(content, journal, day, now)
        if card:                                # 非梦夜/无真实残余 → None → 不做、不造假
            res = dream.inject_dream_card(card, provider=dm.get("provider", "dry_run"))
            if res.get("written"):
                st = state_store.load(STATE)
                dream.mark_dream(st, day)
                state_store.save(st, STATE)


def _tick_growth(now: datetime | None = None) -> None:
    """持续生长：低频率（interval_days）在 GROWTH.md 底子上续长。有真实料才问，没长就不催。"""
    now = now or datetime.now()
    st = state_store.load(STATE)
    gc = _growth_cfg()
    if not growth.should_grow(gc, st, now=now):
        return
    if st.get("last_growth_date"):
        card = growth.build_growth_card_from_store()
        if card:                                # 无真实沉淀 → 不问、不现编
            growth.inject_growth_card(card, provider=gc.get("provider", "dry_run"))
            st = state_store.load(STATE)
            growth.mark_grown(st, now.strftime("%Y-%m-%d"))
            state_store.save(st, STATE)


def register_active(app):
    """① 起 daemon 心跳线程；② 挂 /api/active/* 路由。"""
    start_active_heartbeat()
    app.include_router(router, prefix="/api/active")


# ---------- 路由 ----------

@router.get("/config")
async def get_config():
    return _active_cfg()


@router.post("/config")
async def set_config(payload: dict):
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    # 唯一真相 = 注入通道矩阵：旧键若被前端误带，一律转写进矩阵，不落 active_behavior
    _ROUTE_TO_CHANNEL = {
        "inject_provider": ("motivation", "provider"),
        "grow_provider": ("growth", "provider"),
        "emoji_mode": ("emoji", "provider"),
        "schedule_enabled": ("schedule", "enabled"),
    }
    for key, (ch, field) in _ROUTE_TO_CHANNEL.items():
        if key in payload:
            _set_matrix_channel(ch, {field: payload.pop(key)})
    data.setdefault("active_behavior", {}).update(payload)
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    return _active_cfg()


def _set_matrix_channel(name: str, kw: dict) -> dict | None:
    """写 inject_channels 某条通道的一个字段，落库（失败静默——读侧照样能读）。
    统一走 inject_channels.update（唯一写路径），返回整份矩阵。"""
    try:
        return inject_channels.update(name, cfg_path=CFG, **kw)
    except Exception:            # noqa: BLE001
        log.exception("matrix write failed for %s", name)
        return None


@router.get("/state")
async def get_state():
    return state_store.load(STATE)


@router.post("/reply")
async def on_reply(payload: dict | None = None):
    """登记一次「你真回了」：清未回/断 awaiting/归零渴望并落库。
    供 OpenClaw 侧真回时调用，也方便手动/测试解锁「未回未超限」闸。"""
    quality = float((payload or {}).get("quality", 0.0) or 0.0)
    c = _active_cfg()
    st = state_store.load(STATE)
    nxt = state_machine.on_user_reply(st, c, quality=quality)
    state_store.save(nxt, STATE)
    return {"ok": True,
            "unanswered_count": nxt["unanswered_count"],
            "awaiting_reply": nxt["awaiting_reply"],
            "social_need": nxt["social_need"],
            "last_real_reply": nxt["last_real_reply"]}


@router.post("/sent")
async def on_sent(payload: dict | None = None):
    """登记一次「她真主动发了一条」：记主动/冷却/awaiting/耗精力并落库。
    对应 send_feed 的 __SELF__；供 OpenClaw 侧真实主动发出时调用（也便于手动/测试）。"""
    c = _active_cfg()
    st = state_store.load(STATE)
    nxt = state_machine.on_active_sent(st, c)
    state_store.save(nxt, STATE)
    return {"ok": True,
            "today_active_count": nxt["today_active_count"],
            "awaiting_reply": nxt["awaiting_reply"],
            "last_active_ts": nxt["last_active_ts"],
            "social_need": nxt["social_need"]}


@router.get("/schedule")
async def get_schedule():
    """E3 时间自决：她亲口排的待开时刻 + inbox 原文（读侧，零写）。"""
    return {"pending": scheduler.pending(),
            "inbox": scheduler.read_inbox(),
            "enabled": _active_cfg().get("schedule_enabled", True),
            "cap": _active_cfg().get("schedule_cap", 24)}


@router.get("/diag")
async def get_diag():
    """主动发送链路诊断：哪一环断了，为什么没发。
    只读聚合 window_gates + 摄入文件 + 心跳线程存活。"""
    from active import diag as diagmod
    from active import timing as timingmod
    from . import agent_admin as aa
    d = diagmod.proactive_diag(CFG, STATE)
    try:
        d["latency"] = timingmod.summarize_sessions(aa.SESSIONS_DIR, limit=6)
    except Exception:            # noqa: BLE001 — 不因计时失败让 diag 崩
        d["latency"] = {"error": "读会话轨迹失败"}
    alive = bool(_thread and _thread.is_alive())
    d["python_heartbeat_alive"] = alive
    d["python_heartbeat"] = {
        "alive": alive,
        "note": (
            "Web 后台在跑，状态机每 %s 分钟推进一次、窗口开了就写卡片"
            % d.get("tick_minutes") if alive else
            "Web 后台没在跑 → 状态机从不推进 → 永远不会写动机卡片（先把 backend 跑起来）"),
    }
    return d


@router.get("/life")
async def get_life():
    content = life_content.load_content(CONTENT)
    day = str(datetime.now().date())
    return {
        "now_activity": life_sim.current_activity(content, day, datetime.now().hour),
        "highlights": life_sim.today_highlights(content, day, datetime.now().hour),
    }


@router.get("/content")
async def get_content():
    return life_content.load_content(CONTENT)


@router.post("/content")
async def set_content(payload: dict):
    # 前端文本编辑器直接发整份 life_content（JSON/YAML）文本
    if "yaml" in payload:
        try:
            text = yaml.safe_load(payload["yaml"])
        except yaml.YAMLError as e:
            return JSONResponse({"error": f"YAML 解析失败: {e}"}, status_code=400)
        if isinstance(text, dict):
            life_content.save_content(text, CONTENT)
            return life_content.load_content(CONTENT)
        return JSONResponse({"error": "内容必须是一个对象"}, status_code=400)
    # 结构化合并（Task 11 行为）
    content = life_content.load_content(CONTENT)
    if "habits" in payload:
        content["habits"] = payload["habits"]
    if "favorites" in payload:
        content["favorites"] = payload["favorites"]
    if "schedule" in payload:
        content["schedule"] = payload["schedule"]
    for b in life_content.BUCKETS:
        if payload.get("buckets", {}).get(b) is not None:
            content["buckets"][b] = payload["buckets"][b][:25]
    life_content.save_content(content, CONTENT)
    return content


@router.get("/journal")
async def get_journal():
    return {"text": life_journal.read_journal(),
            "last": life_journal.last_entry_date()}


@router.post("/grow")
async def grow():
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    day = str(datetime.now().date())
    text = life_grower.grow_today(content, journal, day,
                                  provider=_active_cfg().get("grow_provider", "dry_run"))
    if text:
        life_journal.append_entry(day, text)
    return {"text": text, "day": day}


# 主动窗口触发无 web 假身：主动全归状态机+她本人，
# 手动测试走 CLI（python -m active.cli nudge），不借 web 按钮替她开口。
#
# @router.post("/nudge")
# async def nudge():
#     """手动开一次窗口：拼卡片 → injector（dry_run 默认）。测试用·校验按钮。"""
#     content = life_content.load_content(CONTENT)
#     journal = life_journal.read_journal()
#     st = state_store.load(STATE)
#     day = str(datetime.now().date())
#     card = motivation.build_motivation_card(
#         st, content, journal, day,
#         emoji_mode=_active_cfg().get("emoji_mode", "off"))
#     res = injector.inject_motivation(
#         card, provider=_active_cfg().get("inject_provider", "dry_run"))
#     return {"card": card, "inject": res}


@router.get("/emoji/resolve")
async def emoji_resolve(emotion: str = "", keyword: str = "",
                        mode: str = ""):
    """后台试跑（dry-run）：情绪/关键词 → 字符或图 URL。mode 缺省读配置。"""
    cfg = _active_cfg()
    mode = mode or cfg.get("emoji_mode", "off")
    kw = keyword or emotion
    em = emoji_matcher.emotion_from_keyword(kw) or kw.lower()
    out = {"mode": mode, "keyword": kw}
    if mode == "char":
        out["char"] = emoji_matcher.resolve_char(em) if em in emoji_matcher.EMOTIONS else ""
    elif mode == "image":
        out["image"] = emoji_matcher.resolve_image(
            kw, cfg.get("emoji_sources") or ["adesk", "sogou"])
    return out


@router.get("/reflection")
async def reflection_get():
    """反思链路状态：最近反思 + 配置 + 接真状态（两个开关一起决定是否全自动）。"""
    cfg = _reflection_cfg()
    return {"latest": reflection.latest_reflection(),
            "config": cfg,
            "status": reflection.reflection_status(cfg)}


@router.post("/reflection/config")
async def reflection_config_set(payload: dict):
    """两个开关：enabled/provider 归入矩阵（唯一真相）；window 留在 reflection 段。"""
    if "window" in payload and not payload.get("window"):
        payload.pop("window", None)
    if "enabled" in payload or "provider" in payload or "window" in payload:
        _set_matrix_channel("reflection", {
            k: payload[k] for k in ("enabled", "provider") if k in payload})
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    seg = dict(data.get("reflection") or {})
    if "window" in payload:
        seg["window"] = payload["window"]
    data["reflection"] = seg
    if data.get("reflection"):
        CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
    cfg = _reflection_cfg()
    return {"config": cfg, "status": reflection.reflection_status(cfg)}


@router.post("/reflection/trigger")
async def reflection_trigger():
    """手动触发一次反思请求（试跑）：拼卡 → inject（默认 dry_run）。验证用。"""
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    day = str(datetime.now().date())
    card = reflection.build_reflection_card(content, journal, day)
    res = reflection.inject_reflection_card(
        card, provider=_reflection_cfg().get("provider", "dry_run"))
    return {"card": card, "inject": res}


# ---------- 作息 / 日记 / 梦（夜间记忆链路） ----------

def _set_nightly_seg(block: str, payload: dict, allowed: tuple = ("enabled", "provider")) -> None:
    """夜间链路段写回。enabled/provider 一律归于矩阵（唯一真相）；
    段里只留通道特有参数（如 growth.interval_days）。"""
    if "enabled" in payload or "provider" in payload:
        _set_matrix_channel(block, {
            k: payload.pop(k) for k in ("enabled", "provider") if k in payload})
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    seg = dict(data.get(block) or {})
    for k in allowed:
        if k in payload:
            seg[k] = payload[k]
    data[block] = seg
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")


@router.get("/circadian")
async def circadian_get():
    """作息配置 + 今天折算后的就寝/起床（读侧）。"""
    return _current_schedule()


@router.get("/diary")
async def diary_get():
    return {"config": _diary_cfg(), "status": diary.diary_status(_diary_cfg()),
            "latest": diary.latest_diary()}


@router.post("/diary/config")
async def diary_config_set(payload: dict):
    _set_nightly_seg("diary", payload)
    cfg = _diary_cfg()
    return {"config": cfg, "status": diary.diary_status(cfg)}


@router.post("/diary/trigger")
async def diary_trigger():
    """手动写一次日记请求（试跑）：拼卡 → inject（遵守 provider，默认 dry_run）。"""
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    day = str(datetime.now().date())
    card = diary.build_diary_card(content, journal, day)
    res = diary.inject_diary_card(card, provider=_diary_cfg().get("provider", "dry_run"))
    return {"card": card, "inject": res}


@router.get("/dream")
async def dream_get():
    return {"config": _dream_cfg(), "status": dream.dream_status(_dream_cfg()),
            "latest": dream.latest_dream()}


@router.post("/dream/config")
async def dream_config_set(payload: dict):
    _set_nightly_seg("dream", payload)
    cfg = _dream_cfg()
    return {"config": cfg, "status": dream.dream_status(cfg)}


@router.post("/dream/trigger")
async def dream_trigger():
    """手动做一次梦请求（试跑）：拼卡 → inject。非梦夜/无真实残余 → 不造假返回 None。"""
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    day = str(datetime.now().date())
    card = dream.build_dream_card(content, journal, day)
    if card is None:
        return {"card": None, "note": "今天不逢梦夜或昨夜没有真实由头——不做梦（不造假）"}
    res = dream.inject_dream_card(card, provider=_dream_cfg().get("provider", "dry_run"))
    return {"card": card, "inject": res}


# ---------- 自动初始化（从出生长到目标年龄） ----------

@router.get("/init/status")
async def init_status():
    """GROWTH.md 长成状态 + 目标年龄 + 预览请求卡（读侧，不注入）。"""
    from . import setup as setup_mod
    from active import life_init
    baseline = setup_mod.load(CFG)
    target = life_init.resolve_target_age(baseline)
    st = life_init.init_status()
    st["target_age"] = target
    st["card"] = life_init.frame_init_request(
        baseline, target if target is not None else 22) if target else ""
    return st


@router.post("/init/trigger")
async def init_status_trigger():
    """手动触发一次自动初始化：按目标年龄拼成长请求卡 → inject（默认 dry_run）。"""
    from . import setup as setup_mod
    from active import life_init
    baseline = setup_mod.load(CFG)
    target = life_init.resolve_target_age(baseline)
    if not target:
        return {"card": None,
                "inject": None, "target_age": None,
                "note": "还没填目标年龄 → 不能凭空长成（不现编）。先在基础设定填小语年龄。"}
    card = life_init.frame_init_request(baseline, target)
    res = life_init.inject_init_request(
        card, provider=_init_cfg().get("provider", "dry_run"))
    return {"card": card, "inject": res, "target_age": target}


# ---------- 持续生长（在 GROWTH.md 底子上续长） ----------

@router.get("/growth")
async def growth_get():
    return {"config": _growth_cfg(), "status": growth.growth_status(_growth_cfg())}


@router.post("/growth/config")
async def growth_config_set(payload: dict):
    _set_nightly_seg("growth", payload,
                     allowed=("enabled", "interval_days", "provider"))
    cfg = _growth_cfg()
    return {"config": cfg, "status": growth.growth_status(cfg)}


@router.post("/growth/trigger")
async def growth_trigger():
    """手动想看一张今天拼的续长卡：仅试跑（遵守 provider）。没料 → 卡空, 不现编。"""
    st = state_store.load(STATE)
    if not st.get("initialized") or not st.get("last_growth_date"):
        st = growth.mark_grown(st, None)
    card = growth.build_growth_card_from_store()
    if not card:
        return {"card": None, "note": "这段时间没有真实沉淀(反思/承诺·缺席) → 不现编, 她没长就是没长。"}
    res = growth.inject_growth_card(card, provider=_growth_cfg().get("provider", "dry_run"))
    return {"card": card, "inject": res}


# ---------- 注入通道总控（KEY_INJECT_* 统一矩阵） ----------

@router.get("/inject_channels")
async def inject_channels_get():
    """整份矩阵 + 每条通道的元信息（前端渲染总控页一次拿全）。只读，零写。"""
    channels = inject_channels.load(CFG)
    return {"channels": channels,
            "meta": inject_channels.META,
            "status": {name: inject_channels.status(channels, name)
                       for name in channels}}


@router.post("/inject_channels")
async def inject_channels_set(payload: dict):
    """保存整份矩阵（每条 {enabled, provider} 全量可读写）。支持整体或单条合并。"""
    if "channels" in payload and isinstance(payload["channels"], dict):
        channels = inject_channels.load(CFG)
        for name, seg in payload["channels"].items():
            if name not in channels or not isinstance(seg, dict):
                continue
            channels[name].update({
                k: seg[k] for k in ("enabled", "provider") if k in seg})
        out = inject_channels.save(channels, CFG)
    else:                        # 单条 {name: {enabled/provider}} 便捷写
        name = payload.get("name")
        if not name or name not in inject_channels.DEFAULTS:
            return JSONResponse({"error": f"未知通道: {name}"}, status_code=400)
        out = _set_matrix_channel(name, {
            k: payload[k] for k in ("enabled", "provider") if k in payload}) or \
            inject_channels.load(CFG)
    return {"channels": out,
            "status": {n: inject_channels.status(out, n) for n in out}}


# ---------- 记忆·检索盐度（recall_mode） ----------

@router.get("/memory_mode")
async def memory_mode_get():
    """当前 recall_mode + 三档说明 + §记忆 分块预览（只读）。"""
    mode = memory_mode.load_mode(CFG)
    return {"mode": mode, "modes": list(memory_mode.MODES),
            "guidance": memory_mode.GUIDANCE,
            "intake_has_block": memory_mode._BEGIN in _read_intake()}


@router.post("/memory_mode")
async def memory_mode_set(payload: dict):
    """写 memory.recall_mode 并重渲染 PROACTIVE_INTAKE §记忆 分块。"""
    mode = payload.get("mode", "")
    if mode not in memory_mode.MODES:
        return JSONResponse({"error": f"recall_mode 只能是 {list(memory_mode.MODES)}"},
                            status_code=400)
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    mem = dict(data.get("memory") or {})
    mem["recall_mode"] = mode
    data["memory"] = mem
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    block = memory_mode.apply_to_intake(mode)
    return {"mode": mode,
            "block_written": bool(block),
            "guidance": memory_mode.GUIDANCE[mode]}


def _read_intake() -> str:
    try:
        return memory_mode.INTAKE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
