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


def test_social_need_grows_without_reply():
    s = base(social_need=0.0, last_real_reply="2026-08-11T10:00:00")
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0))  # 2h
    assert 0.0 < s1["social_need"] < 1.0


def test_reply_resets_social_need():
    s = base(social_need=0.9, mood=0.2)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0), reply_quality=0.5)
    assert s1["social_need"] == 0.0
    assert s1["awaiting_reply"] is False


def test_anxious_grows_faster_than_avoidant():
    t = datetime(2026, 8, 11, 12, 0)
    sa = sm.tick(base(social_need=0.0, last_real_reply="2026-08-11T10:00:00"),
                 {**CFG, "attachment": "anxious"}, t)
    sv = sm.tick(base(social_need=0.0, last_real_reply="2026-08-11T10:00:00"),
                 {**CFG, "attachment": "avoidant"}, t)
    assert sa["social_need"] > sv["social_need"]


def test_window_closed_when_need_low():
    assert not sm.should_open_window(base(social_need=0.2), CFG, datetime(2026, 8, 11, 14, 0))


def test_window_opens_afternoon():
    assert sm.should_open_window(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 14, 0))


def test_quiet_hours_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 3, 0))


def test_cooldown_blocks():
    s = base(social_need=0.9, energy=80.0, last_active_ts="2026-08-11T13:58:00")
    assert not sm.should_open_window(s, CFG, datetime(2026, 8, 11, 14, 0))


def test_daily_max_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0, today_active_count=2),
                                     CFG, datetime(2026, 8, 11, 14, 0))


def test_unanswered_max_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0, unanswered_count=3),
                                     CFG, datetime(2026, 8, 11, 14, 0))


def test_energy_low_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=10.0), CFG, datetime(2026, 8, 11, 14, 0))


def test_late_night_disabled_blocks():
    cfg = {**CFG, "allow_late_night": False}
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0), cfg, datetime(2026, 8, 11, 0, 0))


def test_active_sent_increments_and_relief():
    s1 = sm.on_active_sent(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 14, 0))
    assert s1["today_active_count"] == 1
    assert s1["social_need"] < 0.9
    assert s1["energy"] < 80.0
    assert s1["awaiting_reply"] is True
    assert s1["last_active_ts"] is not None


# ===================== bond 机制(羁绊/思念) =====================
# 依恋理论: 真实回应/承诺兑现 → 安全基地, 羁绊绛; 缺席/承诺落空 → 关系受威胁,
# 触发"求得亲近"(protest)→ 渴望被点燃, 她忍不住想去找他, 而不是干等。


def test_bond_seeded_from_config_on_init():
    s1 = sm.tick(base(), CFG, datetime(2026, 8, 11, 14, 0))
    assert s1["bond"] == CFG["bond_start"]


def test_bond_stays_in_range():
    s1 = sm.tick(base(), CFG, datetime(2026, 8, 11, 14, 0))
    assert 0 <= s1["bond"] <= CFG["bond_max"]


def test_reply_grows_bond():
    s = base(bond=50.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0), reply_quality=0.5)
    assert s1["bond"] == 50.0 + CFG["bond_grow_per_reply"]


def test_bond_does_not_exceed_max_on_reply():
    s = base(bond=99.9)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0), reply_quality=0.5)
    assert s1["bond"] <= CFG["bond_max"]


def test_deeper_bond_yearns_faster():
    t = datetime(2026, 8, 11, 12, 0)
    lo = sm.tick(base(social_need=0.0, bond=5.0, last_real_reply="2026-08-11T10:00:00"), CFG, t)
    hi = sm.tick(base(social_need=0.0, bond=90.0, last_real_reply="2026-08-11T10:00:00"), CFG, t)
    assert hi["social_need"] > lo["social_need"]


def test_kept_promise_raises_bond():
    s1 = sm.apply_relation_event(base(bond=50.0), CFG, "kept_promise")
    assert s1["bond"] == 50.0 + CFG["kept_promise_gain"]


def test_broken_promise_lowers_bond_and_spikes_need():
    s1 = sm.apply_relation_event(base(bond=50.0, social_need=0.3), CFG, "broken_promise")
    assert s1["bond"] == 50.0 - CFG["broken_promise_drop"]
    assert s1["social_need"] > 0.3


def test_absence_lowers_bond_and_spikes_need():
    s1 = sm.apply_relation_event(base(bond=50.0, social_need=0.3), CFG, "absence")
    assert s1["bond"] == 50.0 - CFG["absence_drop"]
    assert s1["social_need"] > 0.3


def test_relation_threat_floor_at_zero_bond():
    s1 = sm.apply_relation_event(base(bond=4.0), CFG, "broken_promise")
    assert s1["bond"] >= 0.0


def test_kept_promise_warms_mood_but_threat_dips_it():
    k = sm.apply_relation_event(base(bond=50.0, mood=0.0), CFG, "kept_promise")
    b = sm.apply_relation_event(base(bond=50.0, mood=0.2), CFG, "broken_promise")
    assert k["mood"] > 0.0
    assert b["mood"] < 0.2


def test_bond_config_defaults_exist():
    for k in ("bond_start", "bond_max", "bond_grow_per_reply", "bond_thirst",
              "kept_promise_gain", "broken_promise_drop", "absence_drop",
              "threat_spike"):
        assert k in CFG, f"缺少配置默认值 {k}"
