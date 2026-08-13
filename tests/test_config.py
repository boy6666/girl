from pathlib import Path
import active.config as cfg
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


def test_load_config_returns_merged_defaults(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("active_behavior:\n  emoji_media_dir: custom_media\n", encoding="utf-8")
    out = cfg.load_config(p)
    assert out["emoji_media_dir"] == "custom_media"
    assert out["emoji_media_ttl_days"] == 14          # 未在 yaml → 用默认
    assert out["open_threshold"] == 0.5               # merge 后仍有其余默认

def test_load_config_missing_file_uses_defaults():
    out = cfg.load_config(Path("definitely/missing.yaml"))
    assert out["emoji_media_dir"] == "data/media"
