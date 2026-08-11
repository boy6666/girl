from datetime import datetime
from active import life_sim as life


def test_current_activity_empty_bucket_neutral():
    assert life.current_activity({"buckets": {}}, "2026-08-11", 9) == life._NEUTRAL


def test_current_activity_morning_from_user_fact():
    C = {"buckets": {"morning": ["晨跑"]}}
    assert life.current_activity(C, "2026-08-11", 8) == "晨跑"


def test_night_is_sleeping():
    assert life.current_activity({"buckets": {}}, "2026-08-11", 3) == life._SLEEP


def test_highlights_empty_when_no_content():
    assert life.today_highlights({"buckets": {}}, "2026-08-11", 19, 2) == []


def test_highlights_from_user_facts_deterministic():
    C = {"buckets": {"morning": ["晨跑"], "work": ["写代码"],
                     "afternoon": ["散步"], "evening": ["看书"]}}
    a = life.today_highlights(C, "2026-08-11", 19, 2)
    b = life.today_highlights(C, "2026-08-11", 19, 2)
    assert a == b and len(a) == 2


def test_dream_only_in_window_and_needs_residue():
    # 非夜窗 → 无梦
    assert life.maybe_dream("2026-08-11", datetime(2026, 8, 11, 15, 0), "猫") is None
    # 夜窗但无日间残余 → 不硬造
    assert life.maybe_dream("2026-08-11", datetime(2026, 8, 11, 2, 0), "") is None


def test_dream_intermittent_not_every_night():
    nights = [life.maybe_dream(f"2026-08-{d:02d}", datetime(2026, 8, d, 2, 0), "猫")
              for d in range(1, 11)]
    dreams = [n for n in nights if n is not None]
    assert 0 < len(dreams) < len(nights)   # 有梦，但不是每天
