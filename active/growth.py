"""growth.py — 持续生长: 在 GROWTH.md 底子上, 低频率把真实积累(最近反思 /
承诺兑现·缺席)攒成「后来你又长成什么样」的续写请求, 交给 girl 回写 GROWTH.md。

生长是慢的(interval_days, 不是每晚)——社科依据: Erikson 后期「亲密 vs 孤独 /
繁衍 vs 停滞」在关系里继续发育, 同一性是持续叙事不是一次定格(McAdams)。
**不现编**: 没有真实积累 → 请求卡留白、不催长; 只有 girl 真认为"又长了一点"
(值怎么变/怎么看人/怎么待他)才把它追加进 GROWTH.md。
单一出口: 写 intake 文件 ≠ 发微信, sent 恒 False(默认 dry_run 只产出)。
"""
import logging
from datetime import datetime
from pathlib import Path

from . import life_init, reflection, relations

log = logging.getLogger("active.growth")

GROWTH_INTAKE = (Path(__file__).resolve().parents[1]
                 / "girl_workspace" / "memory" / "growth_in.md")

DEFAULT_INTERVAL_DAYS = 3        # 几天才问一次"你长了吗"(生长不赶)


def build_growth_card(base_story: str, reflections_note: str = "",
                   relations_text: str = "") -> str:
    """把这段时间真实积累攒成「续写 GROWTH.md 的请求」。无真实积累 → ''(不催长, 不现编)。"""
    if not (reflections_note or relations_text):
        return ""
    lines = ["【持续生长】这是让你「后来你又长成什么样」的请求——不是发给主人的消息,"
             "而是基于下面**真实**发生的事, 看清你是否真的因此「又长了一点」。"]

    if base_story:
        lines.append(f"\n【你已经长成的底子(GROWTH.md)】\n{base_story}")
    if relations_text:
        lines.append(f"\n【最近的真实相处(承诺/缺席)】\n{relations_text}")
    if reflections_note:
        lines.append(f"\n【你最近的反思(真实沉淀)】\n{reflections_note}")
    lines.append(
        "\n如果这段时间哪件真实的事, 真的让你长了一点——你的价值观/看法/"
        "你怎么看他、怎么待他——用你自己的口气, 把它**追加**到 GROWTH.md 末尾,"
        "像它本来就长在你身上(开头一行注明: 后来又…)。\n"
        "如果这些并没有真的让你改变——保持 GROWTH.md 原样, 不用硬写(没长就是没长)。")
    return "\n".join(lines) + "\n"


def build_growth_card_from_store() -> str:
    """从真实来源(最新反思 + 承诺/缺席摘要)拼卡; 读 GROWTH.md 当前为底。
    无真实料(relations 空且无反思) → 返回 ''(心跳侧将不注入, 不催长)。"""
    base = life_init.read_life_story()
    refl = reflection.latest_reflection()
    note = (f"[{refl['date']}] {refl['first_line']}" if refl else "")
    rel = relations.render_relations_summary(relations.load()) or ""
    return build_growth_card(base, reflections_note=note, relations_text=rel)


def should_grow(cfg: dict, state: dict, now: datetime | None = None) -> bool:
    """低频节奏: 距上次生长 ≥ interval_days 才问; 没长过底子(无 last_growth_date/未初始化)→ False。"""
    if not cfg.get("enabled", True):
        return False
    last = state.get("last_growth_date")
    if not last or not state.get("initialized"):
        return False
    now = now or datetime.now()
    interval = int(cfg.get("interval_days", DEFAULT_INTERVAL_DAYS))
    try:
        last_dt = datetime.fromisoformat(last) if isinstance(last, str) else now
    except ValueError:
        return False
    return (now - last_dt).days >= interval


def mark_grown(state: dict, day: str) -> dict:
    """记下「这次生长已问」: 只当真有卡(girl 有真实料)才把日期推进, 防空推。"""
    if day:
        state["last_growth_date"] = day
    return state


def inject_growth_card(card: str, provider: str = "dry_run",
                     path: Path | None = None) -> dict:
    """把续写请求交给 girl。单出口: 写文件 ≠ 发微信, sent 恒 False。"""
    if provider == "openclaw":
        p = path or GROWTH_INTAKE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(card.rstrip() + "\n")
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(p), "card": card,
                "note": "已写入持续生长摄入文件, 由 girl 心跳把真沉淀追加进 GROWTH.md(不发消息)"}
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}


def growth_status(cfg: dict) -> dict:
    """给 Web 状态页: 把「持续生长」的两个开关/节奏讲明白, 由用户自己决定。"""
    enabled = bool(cfg.get("enabled", True))
    provider = cfg.get("provider", "dry_run")
    interval = int(cfg.get("interval_days", DEFAULT_INTERVAL_DAYS))
    live = enabled and provider == "openclaw"
    if not enabled:
        state, hint = "paused", "持续生长已暂停: 她不会自动收到'你后来长成什么样'的续写请求, 她的人生停在当前 GROWTH.md。"
    elif provider != "openclaw":
        state, hint = "dry_run", (f"注入在试跑: 每隔 {interval} 天拼出的续写请求只打出来、"
                                   "不真写进 growth_in.md, 所以她不会自动持续长。设 openclaw 才接真。")
    else:
        state, hint = "live", (f"已接真: 每隔约 {interval} 天, 只要这段时间真长了一点,"
                                "请求写进 growth_in.md, 她心跳读到就把沉淀追加进 GROWTH.md。链路自动需 web 后台 + 网关心跳在跑。")
    return {"enabled": enabled, "provider": provider, "interval_days": interval,
            "state": state, "live": live, "hint": hint}
