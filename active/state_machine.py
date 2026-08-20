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
    """首次 tick 用 seed 填 energy/mood/bond，并标记已初始化（供 heartbeat 判断）。"""
    s = dict(state)
    if s.get("energy") is None:
        s["energy"] = float(config.get("seed_energy", 80.0))
    if s.get("mood") is None:
        s["mood"] = float(config.get("seed_mood", 0.2))
    if s.get("bond") is None:
        s["bond"] = float(config.get("bond_start", 25.0))
    s["social_need"] = float(s.get("social_need", 0.0) or 0.0)
    s["initialized"] = True
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
        # 被真回 → 羁绊加深（关系的安全基地）
        s["bond"] = _clamp(s["bond"] + config["bond_grow_per_reply"],
                           0.0, config["bond_max"])
    else:
        # 社交需求按时间涨（越久没被真回越渴望）；羁绊越深涨得越凶
        dt_h = _dt_hours(s, now)
        moodn = (s["mood"] + 1) / 2            # 情绪好时更想找(0..1)
        mult = _ATTACH_MULT.get(config.get("attachment", "secure"), 1.0)
        bond_f = 1.0 + (s["bond"] / config["bond_max"]) * config["bond_thirst"]
        grow = (config["growth_rate_per_hour"] * dt_h
                * (0.6 + 0.4 * moodn) * mult * bond_f)
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


def window_gates(state, config, now=None) -> list:
    """逐条列出"主动窗口"的全部守卫：{gate, ok, value, limit, detail}。
    供 should_open_window 判定，也让 Web 后台能逐个显示"卡在哪一条"（debug）。"""
    now = now or datetime.now()
    s = _init(state, config)
    hour = now.hour
    qs, qe = int(config["quiet_start"]), int(config["quiet_end"])
    in_quiet = (qs <= hour < qe) if qs <= qe else (hour >= qs or hour < qe)

    last_a = s.get("last_active_ts")
    cooling = False
    if last_a:
        try:
            t0 = datetime.fromisoformat(last_a)
            cooling = (now - t0).total_seconds() < config["cooldown_seconds"]
        except (TypeError, ValueError):
            cooling = False

    late_blocks = False
    if not config.get("allow_late_night", True):
        late_blocks = (hour >= int(config["late_night_start"])
                      or hour < int(config["early_morning_end"]))

    return [
        {"gate": "渴望足够", "ok": s["social_need"] >= float(config.get("open_threshold", 0.5)),
         "value": round(s["social_need"], 3),
         "limit": f"≥ {config.get('open_threshold', 0.5)}",
         "detail": "越久没被真回，渴望越高"},
        {"gate": "精力在线", "ok": s["energy"] >= 20,
         "value": round(s["energy"], 1), "limit": "≥ 20", "detail": "太累就不开口"},
        {"gate": "不在勿扰时段", "ok": not in_quiet,
         "value": f"{hour:02d}:00", "limit": f"避开 {qs:02d}:00–{qe:02d}:00",
         "detail": "勿扰时间只静默"},
        {"gate": "过了冷却", "ok": not cooling,
         "value": last_a or "—", "limit": f"距上次 ≥ {config['cooldown_seconds']}s",
         "detail": "刚主动过就先歇"},
        {"gate": "未达每日上限", "ok": s["today_active_count"] < config["daily_max"],
         "value": s["today_active_count"],
         "limit": f"< {config['daily_max']}", "detail": "每天最多主动几次"},
        {"gate": "未回未超限", "ok": s["unanswered_count"] < config["max_unanswered"],
         "value": s["unanswered_count"],
         "limit": f"< {config['max_unanswered']}",
         "detail": "ta 没真回就不一直催（回一条消息会清零）"},
        {"gate": "允许深夜", "ok": not late_blocks,
         "value": f"{hour:02d}:00", "limit": f"{config['late_night_start']}:00–{config['early_morning_end']}:00",
         "detail": "深夜开关已关时这一条不通过"},
    ]


def should_open_window(state, config, now=None) -> bool:
    """是否开放一个"主动窗口"（全部守卫满足才 True）。"""
    return all(g["ok"] for g in window_gates(state, config, now))


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


def apply_relation_event(state, config, kind) -> dict:
    """关系事件入状态机（承诺兑现/落空、缺席）。
    kept_promise → 羁绊↑、情绪↑（安全基地）；
    broken_promise/absence → 羁绊↓、渴望瞬间飙升（protest: 关系受威胁时反而更想找他）。
    纯函数：返回新 dict，不改入参。
    """
    s = _init(state, config)
    if kind == "kept_promise":
        s["bond"] = _clamp(s["bond"] + config["kept_promise_gain"],
                           0.0, config["bond_max"])
        s["mood"] = _clamp(s["mood"] + config.get("kept_promise_mood", 0.1),
                           -1.0, 1.0)
    elif kind in ("broken_promise", "absence"):
        drop = (config["broken_promise_drop"] if kind == "broken_promise"
                else config["absence_drop"])
        s["bond"] = _clamp(s["bond"] - drop, 0.0, config["bond_max"])
        s["social_need"] = _clamp(s["social_need"] + config["threat_spike"],
                                  0.0, 1.0)
        s["mood"] = _clamp(s["mood"] - config.get("threat_mood_dip", 0.1),
                           -1.0, 1.0)
    else:
        raise ValueError(f"未知关系事件: {kind}")
    return s
