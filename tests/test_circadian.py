"""test_circadian.py — 作息双向漂移：内驱(自己忙)→早睡，外驱(陪他/他说累)→晚/早。"""
from active import circadian


def test_parse_hhmm():
    assert circadian.parse_hhmm("23:00") == (23, 0)
    assert circadian.parse_hhmm("08:30") == (8, 30)
    assert circadian.parse_hhmm("bad") == (23, 0)


def test_in_band_wrap_midnight():
    # 深夜带 23:00(1380) → 03:00(180)，跨午夜
    assert circadian.in_band(23 * 60 + 30, 1380, 180) is True
    assert circadian.in_band(1 * 60 + 30, 1380, 180) is True
    assert circadian.in_band(21 * 60, 1380, 180) is False
    assert circadian.in_band(9 * 60, 1380, 180) is False


def test_minutes_past_wrap():
    # 01:30 相对 23:00 过了 150 分钟（跨午夜）
    assert circadian.minutes_past(1 * 60 + 30, 23 * 60) == 150


def test_is_wind_down_true():
    assert circadian.is_wind_down("今天好累 我先睡啦")
    assert circadian.is_wind_down("晚安 早点睡")
    assert circadian.is_wind_down("顶不住了 困了")
    assert circadian.is_wind_down("我困了 想睡觉了")


def test_is_wind_down_false():
    assert circadian.is_wind_down("刚到家") is False
    assert circadian.is_wind_down("）") is False
    assert circadian.is_wind_down(None) is False


def test_schedule_base():
    r = circadian.schedule("23:00", "08:00")
    assert r["bedtime"] == "23:00" and r["wake"] == "08:00"
    assert r["note"] == "按点"


def test_schedule_late_shift_keeps_total_sleep():
    # 他聊到 01:30 → 晚睡 150 分钟，起床同量后延
    r = circadian.schedule("23:00", "08:00", last_contact_clock=1 * 60 + 30)
    assert r["bedtime"] == "01:30"
    assert r["wake"] == "10:30"
    assert r["shift_min"] == 150


def test_schedule_late_caps_at_max_shift():
    # 02:50 越就寝 230 分，但 max_shift=120 → 封顶 120
    r = circadian.schedule("23:00", "08:00", last_contact_clock=2 * 60 + 50,
                           max_shift_min=120)
    assert r["shift_min"] == 120
    assert r["wake"] == "10:00"


def test_schedule_morning_contact_no_shift():
    r = circadian.schedule("23:00", "08:00", last_contact_clock=9 * 60)
    assert r["shift_min"] == 0


def test_schedule_own_load_early():
    # 今天她自己真实忙了 3 件事 → 就寝前移 60 分钟
    r = circadian.schedule("23:00", "08:00", own_load=3, own_load_min_per_item=20)
    assert r["bedtime"] == "22:00"
    assert r["wake"] == "07:00"
    assert r["shift_min"] == -60


def test_schedule_own_load_capped_at_early_bedtime():
    r = circadian.schedule("23:00", "08:00", own_load=100,
                           early_bedtime="21:00", own_load_min_per_item=20)
    assert r["bedtime"] == "21:00"
    assert r["wake"] == "06:00"


def test_schedule_wind_down_goes_early():
    r = circadian.schedule("23:00", "08:00", wind_down=True,
                           early_bedtime="21:00")
    assert r["bedtime"] == "21:00" and r["wake"] == "06:00"


def test_schedule_late_beats_wind_down():
    # 真实还在一起（聊到 01:30）→ 晚睡赢，不早收
    r = circadian.schedule("23:00", "08:00", last_contact_clock=1 * 60 + 30,
                           wind_down=True, early_bedtime="21:00")
    assert r["bedtime"] == "01:30"


# ---- own_load 从生活底色读真实引擎 ----
def test_own_load_from_content():
    content = {"buckets": {"morning": ["晨跑"], "work": ["写代码"],
                           "afternoon": [], "evening": []}}
    assert circadian.own_load(content, "2026-08-13") == 2


def test_own_load_empty():
    assert circadian.own_load({"buckets": {}}, "2026-08-13") == 0
