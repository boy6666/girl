"""state_machine.py — 纯函数状态机：energy/mood/social_need 推进 + 决策。"""
import math
from datetime import datetime

_ATTACH_MULT = {"anxious": 1.5, "secure": 1.0, "avoidant": 0.7}


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
        # 社交需求按时间涨（越久没被真回越渴望）
        dt_h = _dt_hours(s, now)
        moodn = (s["mood"] + 1) / 2            # 情绪好时更想找(0..1)
        mult = _ATTACH_MULT.get(config.get("attachment", "secure"), 1.0)
        grow = config["growth_rate_per_hour"] * dt_h * (0.6 + 0.4 * moodn) * mult
        s["social_need"] = _clamp(s["social_need"] + grow, 0.0, 1.0)
        # 未回计数：awaiting_reply 时每心跳 +1（封顶 max_unanswered）
        if s.get("awaiting_reply"):
            s["unanswered_count"] = min(config["max_unanswered"],
                                        s["unanswered_count"] + 1)
        base = config.get("mood_baseline", 0.15)
        k = 1 - math.exp(-1.0 / config["mood_time_constant_min"])
        s["mood"] += (base - s["mood"]) * k

    target = _energy_target(now.hour) * 100.0
    k = 1 - math.exp(-1.0 / config["energy_time_constant_min"])
    s["energy"] = _clamp(s["energy"] + (target - s["energy"]) * k, 0.0, 100.0)
    return s


def _dt_hours(state, now) -> float:
    last = state.get("last_real_reply")
    if not last:
        return 1.0
    try:
        t0 = datetime.fromisoformat(last)
        return max(0.0, (now - t0).total_seconds() / 3600.0)
    except (TypeError, ValueError):
        return 1.0


def should_open_window(state, config, now=None) -> bool:
    """是否开放一个"主动窗口"（全部守卫满足才 True）。"""
    now = now or datetime.now()
    s = _init(state, config)
    if s["social_need"] < float(config.get("open_threshold", 0.5)):
        return False
    if s["energy"] < 20:
        return False

    hour = now.hour
    qs, qe = int(config["quiet_start"]), int(config["quiet_end"])
    in_quiet = (qs <= hour < qe) if qs <= qe else (hour >= qs or hour < qe)
    if in_quiet:
        return False

    last_a = s.get("last_active_ts")
    if last_a:
        try:
            t0 = datetime.fromisoformat(last_a)
            if (now - t0).total_seconds() < config["cooldown_seconds"]:
                return False
        except (TypeError, ValueError):
            pass

    if s["today_active_count"] >= config["daily_max"]:
        return False
    if s["unanswered_count"] >= config["max_unanswered"]:
        return False
    if not config.get("allow_late_night", True):
        if hour >= int(config["late_night_start"]) or hour < int(config["early_morning_end"]):
            return False
    return True


def on_active_sent(state, config, now=None) -> dict:
    """她真主动发了一条：更新计数/冷却/渴望小缓解/耗精力。"""
    now = now or datetime.now()
    s = _init(state, config)
    if s.get("today") != now.strftime("%Y-%m-%d"):
        s["today"] = now.strftime("%Y-%m-%d")
        s["today_active_count"] = 0
    s["today_active_count"] += 1
    s["last_active_ts"] = _iso(now)
    s["awaiting_reply"] = True
    s["social_need"] = _clamp(s["social_need"] - 0.1, 0.0, 1.0)  # 发了≠被理，只小缓解
    s["energy"] = _clamp(s["energy"] - 8.0, 0.0, 100.0)
    return s


def on_user_reply(state, config, now=None, quality=0.0) -> dict:
    """新用户消息到达时调用：归零渴望/未回、记时间、情绪修正。"""
    return tick(state, config, now, reply_quality=quality)
