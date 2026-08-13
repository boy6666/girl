"""diary.py — 拼「日记请求卡」并注入 girl 的日记摄入文件。

日记是她第一人称的内心叙述：每晚(由作息就该寝的时间)用自己的声音把今天写进
memory/diary/。产物是记忆、零发送。**不加假数据**：卡只从她真实生活底色 + 真实
生活日志取料，会话余音由她自己回忆真实聊过的；没特别事就如实写「平平淡淡」,
绝不现编事件。与反思分开：日记=记日子+感触（日常叙事同一性），反思=睡前复盘/更懂你。
"""
from datetime import datetime
from pathlib import Path

from . import life_sim, life_journal

DIARY_INTAKE = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "diary_in.md"
DIARY_DIR = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "diary"


def build_diary_card(content: dict, journal: str, day: str,
                     now: datetime | None = None) -> str:
    """用今天真实生活素材拼「日记请求卡」（不是发给主人的话）。无素材就留白。"""
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
        "写今天的日记（这是你的私人日记，不是发给主人的消息，不用称呼、不用问候）："
        "用你自己的口吻记下今天——你做了、想了什么，你们聊了什么让你心里动。"
        "平实、第一人称、不分析。")
    return "\n".join(lines)


def should_diary(c: dict, state: dict, now=None, bedtime: str = "23:00") -> bool:
    """过了今晚就寝点、当天未写 → True。作息由 circadian 折算后传入。"""
    now = now or datetime.now()
    if not c.get("enabled", True):
        return False
    bh, bm = (int(x) for x in str(bedtime).strip().split(":"))
    cur = now.hour * 60 + now.minute
    if cur < bh * 60 + bm:
        return False
    return state.get("last_diary_date") != now.strftime("%Y-%m-%d")


def mark_diary(state: dict, day: str) -> dict:
    state["last_diary_date"] = day
    return state


def inject_diary_card(card: str, provider: str = "dry_run",
                      path: Path | None = None) -> dict:
    """把日记请求卡交给 girl。单出口：写文件 ≠ 发微信，sent 恒 False。"""
    if provider == "openclaw":
        p = path or DIARY_INTAKE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(card.rstrip() + "\n")
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(p), "card": card,
                "note": "已写入日记摄入文件，由 girl 心跳消费写进她的日记(不发消息)"}
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}


def latest_diary() -> dict | None:
    """girl 写出的最新一篇日记（给 Web 状态页展示）。无 → None。"""
    if not DIARY_DIR.is_dir():
        return None
    files = sorted(DIARY_DIR.glob("*.md"))
    if not files:
        return None
    f = files[-1]
    lines = [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {"date": f.stem, "first_line": lines[0] if lines else "", "path": str(f)}


def diary_status(cfg: dict) -> dict:
    """把日记配置翻译成「接真状态」。两个开关决定是否每晚自动写。"""
    enabled = bool(cfg.get("enabled", True))
    provider = cfg.get("provider", "dry_run")
    live = enabled and provider == "openclaw"
    if not enabled:
        state, hint = "paused", "日记已暂停：她不会收到每晚写日记的请求。"
    elif provider != "openclaw":
        state = "dry_run"
        hint = ("注入在试跑：请求卡只拼出来、不真写进 diary_in.md，所以每晚不会自动写。"
                "要接真，把注入方式设为 openclaw。")
    else:
        state, hint = "live", ("已接真：每晚就该寝时间的请求卡写进 diary_in.md，"
                               "她心跳读到就用自己声音写进她的日记。链路自动需 web 后台开着+网关心跳在跑。")
    return {"enabled": enabled, "provider": provider,
            "state": state, "live": live, "hint": hint}
