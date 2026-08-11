"""motivation.py — 生成"动机卡片"：注入给 girl agent 的文本。

卡片只讲"她此刻在干嘛、今天经历过什么、延续了昨天什么、现在什么状态 + 想不想主动"，
说不说、说什么，完全由 agent 用自己的 SOUL 决定。
原则（用户确认）：不现编内容——今天/昨天/梦都是真的有才写，没有就留白。
"""
from datetime import datetime

from . import life_journal, life_sim


def _state_words(s: dict) -> str:
    e = s.get("energy")
    if e is None:
        now = "精神还行"
    elif e < 35:
        now = "累"
    elif e < 65:
        now = "还行"
    else:
        now = "精神不错"
    m = s.get("mood")
    if m is None:
        mood = "情绪平稳"
    elif m < 0:
        mood = "情绪有点低落"
    elif m > 0.3:
        mood = "心情不错"
    else:
        mood = "情绪平稳"
    return f"精力{now}，{mood}"


def build_motivation_card(state: dict, content: dict, journal: str, day: str,
                          now: datetime | None = None) -> str:
    now = now or datetime.now()
    act = life_sim.current_activity(content, day, now.hour)
    highs = life_sim.today_highlights(content, day, now.hour)
    prev = life_journal.recent_entries_from_text(journal, 1)
    # 梦境 = 日间残余(今天高光或最近日志)，非每日；没有则无【梦】段
    residue = (highs[0] if highs else (prev[0] if prev else None))
    dream = life_sim.maybe_dream(day, now, residue)

    lines = [f"【现在】{act}"]
    if highs:
        lines.append("【今天】" + "；".join(highs))
    if prev:
        lines.append(f"【昨天】{prev[0]}")
    if dream:
        lines.append(f"【梦】{dream}")
    lines.append(f"【状态】{_state_words(state)}，有点想你，但我不必现在就说")
    return "\n".join(lines)
