"""state_machine.py — 纯函数状态机：energy/mood/social_need 推进 + 决策。"""
import math
from datetime import datetime


def _energy_target(hour: int) -> float:
    """作息曲线 → 目标精力 (0-1)。午后高、深夜低。"""
    if hour < 6:
        return 0.25
    if hour < 10:
        return 0.6
    if hour < 14:
        return 0.75
    if hour < 19:
        return 0.9
    if hour < 23:
        return 0.6
    return 0.3


def _iso(now: datetime) -> str:
    return now.isoformat(timespec="seconds")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _init(state, config):
    """首次 tick 用 seed 填 energy/mood。"""
    s = dict(state)
    if s.get("energy") is None:
        s["energy"] = float(config.get("seed_energy", 80.0))
    if s.get("mood") is None:
        s["mood"] = float(config.get("seed_mood", 0.2))
    s["social_need"] = float(s.get("social_need", 0.0) or 0.0)
    return s


def tick(state, config, now=None, reply_quality=None) -> dict:
    """推进一个心跳。纯函数：返回新 dict，不改 state。"""
    now = now or datetime.now()
    s = _init(state, config)

    if s.get("today") != now.strftime("%Y-%m-%d"):
        s["today"] = now.strftime("%Y-%m-%d")
        s["today_active_count"] = 0

    if reply_quality is not None:
        s["social_need"] = 0.0
        s["unanswered_count"] = 0
        s["awaiting_reply"] = False
        s["last_real_reply"] = _iso(now)
        s["mood"] = _clamp(s["mood"] + 0.3 * reply_quality, -1.0, 1.0)
    else:
        base = config.get("mood_baseline", 0.15)
        k = 1 - math.exp(-1.0 / config["mood_time_constant_min"])
        s["mood"] += (base - s["mood"]) * k

    target = _energy_target(now.hour) * 100.0
    k = 1 - math.exp(-1.0 / config["energy_time_constant_min"])
    s["energy"] = _clamp(s["energy"] + (target - s["energy"]) * k, 0.0, 100.0)
    return s
