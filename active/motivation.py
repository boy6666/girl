"""motivation.py — 生成"动机卡片"：注入给 girl agent 的文本。

卡片只讲"她此刻在干嘛、今天经历过什么、延续了昨天什么、现在什么状态 + 想不想主动"，
说不说、说什么，完全由 agent 用自己的 SOUL 决定。
原则（用户确认）：不现编内容——今天/昨天/梦都是真的有才写，没有就留白。
"""
from datetime import datetime

from . import life_journal, life_sim, emoji_matcher, emoji_media


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


def _emoji_suggestion(state: dict, mode: str, resolver) -> str:
    if mode == "off":
        return ""
    em = emoji_matcher.mood_to_emotion(state.get("mood"), state.get("energy"))
    if not em:
        return ""
    if mode == "char":
        return f"【表情】此刻情绪合适用「{emoji_matcher.resolve_char(em)}」这种，一个就够"
    if mode == "image":
        local, _provider = (resolver or emoji_media.resolve_to_local)(em)
        if not local:
            return ""                       # 图源失败 → 优雅省略，退回纯文字主动
        return (f"【表情】图={local}（想发就用 message(action=send, path=这路径) ；"
                f"表情包本身有字，默认单发这一张；想配文字就在前/后加一句）")
    return ""


def build_motivation_card(state: dict, content: dict, journal: str, day: str,
                          now: datetime | None = None,
                          emoji_mode: str = "off",
                          emoji_resolver=None,
                          relations: dict | None = None) -> str:
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
    if relations:
        from .relations import render_relations_summary
        xs = render_relations_summary(relations)
        if xs:
            lines.append("【心事】" + xs)
    lines.append(f"【状态】{_state_words(state)}，有点想你，但我不必现在就说")
    hint = _emoji_suggestion(state, emoji_mode, emoji_resolver)
    if hint:
        lines.append(hint)
    return "\n".join(lines)
