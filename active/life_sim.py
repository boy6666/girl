"""life_sim.py — 用生活内容库给出"当下生活片段"与（非每日的）梦境。

原则（用户确认）：无现编内容；只用用户填过的真实事实（bucket 里有才取），
没有就平淡留白。梦境按 Hall & Van de Castle 的 day-residue（日间残余）——
哪天梦里掺着当天惦记的事，且**不是每天都有梦**（确定性稀疏闸门）。
"""
import hashlib
import random
from datetime import datetime

_SLEEP = "在睡觉"
_NEUTRAL = "在忙今天的日常"

# 梦境频率：约每 _DREAM_DEN 晚 _DREAM_NUM 晚（默认约 1/3，非每日）
_DREAM_NUM, _DREAM_DEN = 1, 3


def _bucket(hour: int) -> str:
    if hour < 6:
        return "sleep"
    if hour < 10:
        return "morning"
    if hour < 14:
        return "work"
    if hour < 17:
        return "afternoon"
    if hour < 23:
        return "evening"
    return "sleep"


_CYCLE = ("morning", "work", "afternoon", "evening")


def current_activity(content: dict, day: str, hour: int) -> str:
    """她此刻在干嘛：bucket 有用户填的事实才取；没有/睡眠则给中性留白。"""
    b = _bucket(hour)
    if b == "sleep":
        return _SLEEP
    pool = content.get("buckets", {}).get(b, [])
    if not pool:
        return _NEUTRAL
    return random.Random(f"{day}:{b}").choice(pool)


def today_highlights(content: dict, day: str, hour: int, count: int = 2) -> list[str]:
    """今天过分时段的生活片段（bucket 有内容才出；没有就是空白）。"""
    if hour < 6 or _bucket(hour) == "sleep":
        idx = 4
    else:
        idx = _CYCLE.index(_bucket(hour)) + 1
    out = []
    for i in range(min(idx, len(_CYCLE))):
        b = _CYCLE[i]
        pool = content.get("buckets", {}).get(b, [])
        if pool:
            out.append(random.Random(f"{day}:{b}").choice(pool))
    return out[:count]


def _dream_night(day: str) -> bool:
    """确定性（跨进程稳定）稀疏闸门：今天是否夜里会做梦。"""
    h = int(hashlib.md5(day.encode()).hexdigest(), 16)
    return (h % _DREAM_DEN) < _DREAM_NUM


def maybe_dream(day: str, now: datetime, residue: str | None = None) -> str | None:
    """夜窗 + 非每日 + 有日间残余 → 一梦；否则 None（不硬造、不是每天）。"""
    if not (0 <= now.hour < 8):
        return None
    if not _dream_night(day):
        return None
    if not residue:
        return None
    return f"梦见{residue}，醒来有点恍惚。"
