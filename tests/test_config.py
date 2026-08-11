from active import config as c


def test_defaults_exist():
    assert c.CONFIG_DEFAULTS["open_threshold"] == 0.5
    assert c.CONFIG_DEFAULTS["daily_max"] == 2
    assert c.CONFIG_DEFAULTS["quiet_start"] == 2
    assert c.CONFIG_DEFAULTS["quiet_end"] == 5
    assert c.CONFIG_DEFAULTS["max_unanswered"] == 3
    assert c.CONFIG_DEFAULTS["attachment"] == "secure"


def test_merge_overrides_and_ignores_unknown():
    merged = c.merge_config({"open_threshold": 0.7, "bogus": 1})
    assert merged["open_threshold"] == 0.7
    assert merged["daily_max"] == 2
    assert "bogus" not in merged
