from active import heartbeat, state_store


def test_tick_once_initializes_and_persists(tmp_path):
    cfg = {"tick_minutes": 15, "seed_energy": 80.0, "seed_mood": 0.2,
           "growth_rate_per_hour": 0.12}
    p = tmp_path / "state.json"
    st = state_store.default_state()
    state_store.save(st, p)
    nxt = heartbeat.tick_once(state_store.load(p), state_store.default_state(),
                              cfg, p)
    # 首次 tick 应初始化（填 energy/mood 并标记 initialized），并落盘到同文件
    saved = state_store.load(p)
    assert saved["energy"] is not None
    assert saved["social_need"] >= 0.0
    assert saved["initialized"] is True
    assert nxt["energy"] == saved["energy"]
