from datetime import datetime
from active import config as c, state_machine as sm

CFG = c.CONFIG_DEFAULTS


def base(**over):
    s = {
        "energy": 80.0, "mood": 0.0, "social_need": 0.0,
        "last_real_reply": None, "last_active_ts": None,
        "unanswered_count": 0, "today_active_count": 0,
        "today": "2026-08-11", "awaiting_reply": False,
    }
    s.update(over)
    return s


def test_energy_rises_toward_afternoon_target():
    s = base(energy=60.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0))  # 下午目标 ~90
    assert 60.0 < s1["energy"] <= 90.0


def test_energy_falls_at_night():
    s = base(energy=80.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 23, 0))  # 夜间目标 ~30
    assert s1["energy"] < 80.0


def test_tick_is_pure_and_mood_drifts_to_baseline():
    s = base(mood=0.8)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0))
    assert s["mood"] == 0.8          # 入参没被改
    assert s1["mood"] < 0.8          # 向基线 0.15 飘


def test_reply_bumps_mood_positive():
    s = base(mood=0.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0), reply_quality=0.8)
    assert s1["mood"] > 0.0
