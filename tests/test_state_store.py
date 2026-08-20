from datetime import datetime
from active import state_store


def test_default_state_keys(tmp_path):
    s = state_store.default_state(datetime(2026, 8, 11, 12, 0))
    for k in ("energy", "mood", "social_need", "last_real_reply",
              "last_active_ts", "unanswered_count", "today_active_count",
              "today", "awaiting_reply"):
        assert k in s
    assert s["today"] == "2026-08-11"
    assert s["social_need"] == 0.0
    assert s["awaiting_reply"] is False


def test_load_missing_returns_default(tmp_path):
    assert state_store.load(tmp_path / "none.json")["social_need"] == 0.0


def test_save_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    state_store.save(state_store.default_state(datetime(2026, 8, 11)), p)
    assert state_store.load(p)["today"] == "2026-08-11"


def test_default_state_has_last_reflection_date():
    from active import state_store
    d = state_store.default_state()
    assert "last_reflection_date" in d
    assert d["last_reflection_date"] is None


def test_bond_persisted_across_save_load(tmp_path):
    p = tmp_path / "state.json"
    s = state_store.default_state(datetime(2026, 8, 11))
    s.update({"bond": 42.0, "social_need": 0.7, "awaiting_reply": True})
    state_store.save(s, p)
    loaded = state_store.load(p)
    assert loaded["bond"] == 42.0      # 关系羁绊必须持久化, 不能重载丢
