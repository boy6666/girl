from pathlib import Path
import active.config as cfg
from active import config as c


def test_defaults_exist():
    assert c.CONFIG_DEFAULTS["open_threshold"] == 0.5
    assert c.CONFIG_DEFAULTS["schedule_enabled"] is True
    assert c.CONFIG_DEFAULTS["schedule_cap"] == 24
    assert c.CONFIG_DEFAULTS["attachment"] == "secure"
    # 2026-08-21 grill 拍板：四扇卫门拆了，默认值里不该再有它们
    for gone in ("cooldown_seconds", "daily_max", "quiet_start", "quiet_end",
                 "max_unanswered"):
        assert gone not in c.CONFIG_DEFAULTS, f"{gone} 已被拆，不该留在默认里"


def test_merge_overrides_and_ignores_unknown():
    merged = c.merge_config({"open_threshold": 0.7, "bogus": 1})
    assert merged["open_threshold"] == 0.7
    assert merged["schedule_cap"] == 24
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


def test_reflection_defaults_and_override():
    from active import config as c
    assert c.load_reflection_config.__name__
    assert c.REFLECTION_DEFAULTS == {
        "enabled": True, "window": "22:00", "provider": "dry_run"}
    merged = c.merge_reflection_config({"provider": "openclaw", "bogus": 1})
    assert merged["provider"] == "openclaw"
    assert merged["window"] == "22:00"      # 未知键被忽略


def test_load_reflection_config_missing_file_defaults():
    from active import config as c
    merged = c.merge_reflection_config({})
    assert merged["enabled"] is True and merged["provider"] == "dry_run"
