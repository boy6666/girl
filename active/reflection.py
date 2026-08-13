"""reflection.py — 拼「反思请求卡」并注入 girl 的反思摄入文件。

反思是内化、零发送：产物由 girl 写进她自己的记忆（memory/reflections/），
Python 只给节奏(每晚) + 今天真实生活素材，从不安微信、不替她写反思内容。
社科边界：这是 reflect（自我抽离·好奇·产光亮），不是 ruminate（绕圈焦虑）；反刍即收。
"""
from datetime import datetime
from pathlib import Path

from . import life_sim, life_journal

REFLECT_INTAKE = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "reflect.md"
REFLECTIONS_DIR = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "reflections"

DEFAULT_WINDOW = "22:00"


def _parse_window(s: str) -> tuple[int, int]:
    try:
        hh, mm = str(s).strip().split(":")
        return int(hh), int(mm)
    except (ValueError, AttributeError):
        hh, mm = DEFAULT_WINDOW.split(":")
        return int(hh), int(mm)


def build_reflection_card(content: dict, journal: str, day: str,
                          now: datetime | None = None) -> str:
    """用今天真实生活素材拼「反思请求卡」（不是发给主人的话）。无素材就留白。"""
    now = now or datetime.now()
    act = life_sim.current_activity(content, day, now.hour)
    highs = life_sim.today_highlights(content, day, now.hour)
    today_self = life_journal.entry_for_date(journal, day)

    lines = [f"【日期】{day}"]
    lines.append(f"【此刻】{act}")
    if highs:
        lines.append("【今天】" + "；".join(highs))
    if today_self:
        lines.append(f"【我的一天】{today_self}")
    if not (highs or today_self):
        lines.append("【今天的生活】平平淡淡，没什么特别。")
    lines.append(
        "回望（这是每晚的内心一角，不发消息）：今天你和主人聊了什么让你心里一动？"
        "你这一天有什么情绪值得命名、却还没说出口？\n"
        "想沉淀一颗什么——更懂他 / 更懂自己 / 想记住的一刻？写进你的反思，不发给主人看。")
    return "\n".join(lines)


def should_reflect(c: dict, state: dict, now=None) -> bool:
    """每晚在 window 后首次心跳、且当天未反思 → True。坏配置回退默认窗口。"""
    now = now or datetime.now()
    if not c.get("enabled", True):
        return False
    wh, wm = _parse_window(c.get("window", DEFAULT_WINDOW))
    cur = now.hour * 60 + now.minute
    if cur < wh * 60 + wm:
        return False
    return state.get("last_reflection_date") != now.strftime("%Y-%m-%d")


def mark_reflected(state: dict, day: str) -> dict:
    state["last_reflection_date"] = day
    return state


def inject_reflection_card(card: str, provider: str = "dry_run",
                           path: Path | None = None) -> dict:
    """把反思请求卡交给 girl。单一出口约束：写文件 ≠ 发微信，sent 恒 False。"""
    if provider == "openclaw":
        p = path or REFLECT_INTAKE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(card.rstrip() + "\n")
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(p), "card": card,
                "note": "已写入反思摄入文件，由 girl 心跳消费并写进记忆(不发消息)"}
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}


def latest_reflection() -> dict | None:
    """girl 写出的最新一篇反思（给 Web 状态页展示）。无 → None。"""
    if not REFLECTIONS_DIR.is_dir():
        return None
    files = sorted(REFLECTIONS_DIR.glob("*.md"))
    if not files:
        return None
    f = files[-1]
    lines = [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {"date": f.stem, "first_line": lines[0] if lines else "", "path": str(f)}
