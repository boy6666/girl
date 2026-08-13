"""dream.py — 拼「梦记请求卡」并注入 girl 的梦摄入文件。

梦是非每日的（约 1/3 夜），由头 = **昨天的真实日间残余**（day-residue，Hall & Van de
Castle：梦把前一天惦记的事掺进来）。girl 在今早起床点后用自己的声音把「昨夜之梦」
写进 memory/dreams/。产物是记忆、零发送。**不加假数据**：昨天没有真实素材或不逢梦夜
→ 就不做（None），绝不硬造一个梦。
"""
from datetime import datetime, timedelta
from pathlib import Path

from . import life_sim, life_journal

DREAM_INTAKE = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "dream_in.md"
DREAMS_DIR = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "dreams"


def previous_day(day: str) -> str:
    return (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")


def day_residue(content: dict, journal: str, day: str) -> list[str]:
    """昨天真实的日间残余（生活底色 + 昨天生活日志）。无真实素材 → []。"""
    prev = previous_day(day)
    highs = life_sim.today_highlights(content, prev, 23)
    jy = life_journal.entry_for_date(journal, prev)
    parts = list(highs)
    if jy:
        parts.append(jy)
    return [p for p in parts if p]


def build_dream_card(content: dict, journal: str, day: str,
                     now: datetime | None = None) -> str | None:
    """拼「梦记请求卡」。非梦夜或无真实残余 → None（不做梦、不硬造）。"""
    prev = previous_day(day)
    if not life_sim._dream_night(prev):
        return None
    residue = day_residue(content, journal, day)
    if not residue:
        return None
    lines = [f"【日期】{day}", "【昨夜由头】" + "；".join(residue)]
    lines.append(
        "写昨晚的梦（这是你的记忆，不是发给主人的消息）：把上面的日间残余织进"
        "昨夜梦里，用你自己的口吻写下这场梦。梦可以自由、跳跃、不合逻辑——但它"
        "只从你昨晚真实惦记的事里长出来，不外编别的。")
    return "\n".join(lines)


def should_dream(c: dict, state: dict, now=None, wake: str = "08:00") -> bool:
    """过了今早起床点、当天未写梦记 → True。作息由 circadian 折算后传入。"""
    now = now or datetime.now()
    if not c.get("enabled", True):
        return False
    wh, wm = (int(x) for x in str(wake).strip().split(":"))
    cur = now.hour * 60 + now.minute
    if cur < wh * 60 + wm:
        return False
    return state.get("last_dream_date") != now.strftime("%Y-%m-%d")


def mark_dream(state: dict, day: str) -> dict:
    state["last_dream_date"] = day
    return state


def inject_dream_card(card: str, provider: str = "dry_run",
                      path: Path | None = None) -> dict:
    """把梦记请求卡交给 girl。单出口：写文件 ≠ 发微信，sent 恒 False。"""
    if provider == "openclaw":
        p = path or DREAM_INTAKE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(card.rstrip() + "\n")
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(p), "card": card,
                "note": "已写入梦摄入文件，由 girl 心跳消费写进她的梦记(不发消息)"}
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}


def latest_dream() -> dict | None:
    """girl 写出的最新一篇梦记（给 Web 状态页展示）。无 → None。"""
    if not DREAMS_DIR.is_dir():
        return None
    files = sorted(DREAMS_DIR.glob("*.md"))
    if not files:
        return None
    f = files[-1]
    lines = [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {"date": f.stem, "first_line": lines[0] if lines else "", "path": str(f)}


def dream_status(cfg: dict) -> dict:
    """把梦配置翻译成「接真状态」。两个开关决定是否做非每日梦。"""
    enabled = bool(cfg.get("enabled", True))
    provider = cfg.get("provider", "dry_run")
    live = enabled and provider == "openclaw"
    if not enabled:
        state, hint = "paused", "梦已暂停：她不会再做梦记。"
    elif provider != "openclaw":
        state = "dry_run"
        hint = ("注入在试跑：请求卡只拼出来、不真写进 dream_in.md，所以不会自动做。"
                "要接真，把注入方式设为 openclaw。")
    else:
        state, hint = "live", ("已接真：逢梦夜·有真实昨日残余时，请求卡写进 dream_in.md，"
                               "她心跳读到就用自己声音写下昨夜之梦。链路自动需 web 后台开着+网关心跳在跑。")
    return {"enabled": enabled, "provider": provider,
            "state": state, "live": live, "hint": hint}
