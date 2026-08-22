"""inject_channels — 注入通道总控：默认、load/save 往返、overlay、status。
唯一真相= data/config.yaml 的 inject_channels 段；emoji 只认 off|image（char 已废弃，
违反 dbf8331 消息禁emoji字符）。"""
import yaml

from active import inject_channels as ic


def test_defaults_no_yaml(tmp_path):
    ch = ic.load(tmp_path / "nope.yaml")
    assert set(ch) == set(ic.DEFAULTS)
    assert ch["emoji"]["provider"] == "image"          # 表情包目标档
    assert "char" not in ic.META["emoji"]["providers"]  # char 已废弃
    assert ch["perception"]["enabled"] is False


def test_emoji_char_deprecated():
    assert ic.DEFAULTS["emoji"]["provider"] == "image"
    assert ic.META["emoji"]["providers"] == ["off", "image"]


def test_load_merges_partial(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("inject_channels:\n  motivation: {enabled: false}\n",
                   encoding="utf-8")
    ch = ic.load(cfg)
    assert ch["motivation"]["enabled"] is False
    assert ch["motivation"]["provider"] == "openclaw"   # 未写 provider 保默认
    assert ch["reflection"]["enabled"] is True           # 没写的整条保默认


def test_save_roundtrip_preserves_other_sections(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("personality:\n  sweetness: 65\n", encoding="utf-8")
    ch = ic.load(cfg)
    ch["dream"]["provider"] = "openclaw"
    ic.save(ch, cfg)
    again = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    assert again["personality"]["sweetness"] == 65
    assert again["inject_channels"]["dream"]["provider"] == "openclaw"


def test_on_and_provider(tmp_path):
    ch = ic.load(tmp_path / "nope.yaml")
    assert ic.on(ch, "schedule") is True
    assert ic.provider(ch, "emoji") == "image"
    ch2 = dict(ch, emoji={"enabled": False, "provider": "off"})
    assert ic.on(ch2, "emoji") is False


def test_status_flag(tmp_path):
    ch = ic.load(tmp_path / "nope.yaml")
    assert ic.status(ch, "motivation") == "live"        # openclaw → live
    assert ic.status(ch, "dream") == "trial"            # dry_run → trial
    ch2 = dict(ch, perception={"enabled": False, "provider": "none"})
    assert ic.status(ch2, "perception") == "off"


def test_overlay_active_applies_matrix(tmp_path):
    ch = ic.load(tmp_path / "nope.yaml")
    base = {"open_threshold": 0.5, "emoji_mode": "off",
            "inject_provider": "dry_run", "grow_provider": "dry_run",
            "schedule_enabled": False, "schedule_cap": 24}
    out = ic.overlay_active(base, ch)
    assert out["emoji_mode"] == "image"                 # 矩阵覆盖旧默认
    assert out["inject_provider"] == "openclaw"
    assert out["grow_provider"] == "openclaw"
    assert out["schedule_enabled"] is True
    assert out["open_threshold"] == 0.5                 # 非通道键不动
    assert out["schedule_cap"] == 24


def test_update_single_channel(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "inject_channels:\n  dream: {enabled: true, provider: dry_run}\n",
        encoding="utf-8")
    out = ic.update("dream", cfg_path=cfg, enabled=False)
    assert out["dream"]["enabled"] is False
    assert ic.load(cfg)["dream"]["enabled"] is False
