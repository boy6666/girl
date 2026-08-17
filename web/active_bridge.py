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
                    circadian, diary, dream, life_init, growth)
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
    # 自动窗口也读 inject_provider（与 /nudge 一致）：dry_run 只打印；
    # openclaw 把卡片写进心跳文件由小语决定说不说。默认 dry_run，可回滚。
    return injector.inject_motivation(
        card, provider=_active_cfg().get("inject_provider", "dry_run"))


def _heartbeat_loop():
    while True:
        try:
            c = _active_cfg()
            st = state_store.load(STATE)
            init = state_store.default_state()
            nxt = state_machine.tick(st if st.get("initialized") else init, c)
            state_store.save(nxt, STATE)
            if state_machine.should_open_window(nxt, c):
                content = life_content.load_content(CONTENT)
                journal = life_journal.read_journal()
                card = motivation.build_motivation_card(
                    nxt, content, journal, str(datetime.now().date()),
                    emoji_mode=c.get("emoji_mode", "off"))
                _on_window(card)
                st2 = state_machine.on_active_sent(nxt, c)
                state_store.save(st2, STATE)
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
    return cfgmod.merge_config(c)


def _reflection_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "reflection") or {}
        except yaml.YAMLError:
            raw = {}
    return cfgmod.merge_reflection_config(raw)


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
    return cfgmod.merge_diary_config(raw)


def _init_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "init") or {}
        except yaml.YAMLError:
            raw = {}
    return {"provider": raw.get("provider", "dry_run")}


def _growth_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "growth") or {}
        except yaml.YAMLError:
            raw = {}
    return cfgmod.merge_growth_config(raw)
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
    return cfgmod.merge_dream_config(raw)


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
    data.setdefault("active_behavior", {}).update(payload)
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    return _active_cfg()


@router.get("/state")
async def get_state():
    return state_store.load(STATE)


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


@router.post("/nudge")
async def nudge():
    """手动开一次窗口：拼卡片 → injector（dry_run 默认）。测试用·校验按钮。"""
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    st = state_store.load(STATE)
    day = str(datetime.now().date())
    card = motivation.build_motivation_card(
        st, content, journal, day,
        emoji_mode=_active_cfg().get("emoji_mode", "off"))
    res = injector.inject_motivation(
        card, provider=_active_cfg().get("inject_provider", "dry_run"))
    return {"card": card, "inject": res}


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
    """让用户在后台自己决定两个开关：enabled（每晚反思）/ provider（dry_run|openclaw）。"""
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    seg = dict(data.get("reflection") or {})
    for k in ("enabled", "window", "provider"):
        if k in payload:
            seg[k] = payload[k]
    data["reflection"] = seg
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
