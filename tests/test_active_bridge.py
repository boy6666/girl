"""test_active_bridge.py — 自动主动窗口的注入契约：读 inject_provider 配置。
默认 dry_run 无副作用；翻成 openclaw 时只写心跳文件、sent 恒 False（单一出口）。
"""
import yaml

from active import injector
from web import active_bridge


def test_on_window_defaults_to_dry_run(monkeypatch):
    # 默认配置（无 inject_provider）→ 只打印，不写文件、不发
    monkeypatch.setattr(active_bridge, "_active_cfg", lambda: {})
    r = active_bridge._on_window("【现在】在看书")
    assert r["dry_run"] is True
    assert r["sent"] is False


def test_on_window_openclaw_writes_card_not_sends(monkeypatch, tmp_path):
    hp = tmp_path / "memory" / "heartbeat.md"
    monkeypatch.setattr(injector, "HEARTBEAT_PATH", hp)
    monkeypatch.setattr(active_bridge, "_active_cfg",
                        lambda: {"inject_provider": "openclaw"})
    r = active_bridge._on_window("【现在】在看书")
    assert r["sent"] is False          # 写文件 ≠ 发微信
    assert r["written"] is True
    assert hp.read_text(encoding="utf-8") == "【现在】在看书\n"


import asyncio  # noqa: E402


def test_emoji_resolve_char_backend():
    from web.active_bridge import emoji_resolve
    out = asyncio.run(emoji_resolve(emotion="开心", keyword="", mode="char"))
    assert out["mode"] == "char"
    assert out["keyword"] in ("开心", "joy")
    assert out["char"]          # 非空——解析出一个字符


def test_emoji_resolve_image_backend_defaults_to_config(monkeypatch):
    monkeypatch.setattr(active_bridge, "_active_cfg",
                        lambda: {"emoji_mode": "image",
                                 "emoji_sources": ["adesk"]})
    monkeypatch.setattr(
        active_bridge.emoji_matcher, "_http_get_json",
        lambda *a, **k: {"res": {"data": [{"url": "https://x/a.png"}]}})
    out = asyncio.run(active_bridge.emoji_resolve(keyword="开心", emotion="", mode=""))
    assert out["mode"] == "image"
    assert out["image"]["provider"] == "adesk"


def test_inject_reflection_defaults_to_dry_run(monkeypatch, tmp_path):
    from active import reflection
    r = reflection.inject_reflection_card("【日期】2026-08-13", "dry_run",
                                          path=tmp_path / "r.md")
    assert r["dry_run"] is True and r["sent"] is False
    assert not (tmp_path / "r.md").exists()


def test_reflection_cfg_merges_top_level(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "reflection:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    rc = active_bridge._reflection_cfg()
    assert rc["provider"] == "openclaw"
    assert rc["window"] == "22:00"   # 默认被保留


def test_reflection_endpoint_reports_latest(monkeypatch, tmp_path):
    import asyncio
    d = tmp_path / "reflections"
    d.mkdir()
    (d / "2026-08-13.md").write_text("今天更懂你了\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge.reflection, "REFLECTIONS_DIR", d)
    out = asyncio.run(active_bridge.reflection_get())
    assert out["latest"]["date"] == "2026-08-13"
    assert out["latest"]["first_line"] == "今天更懂你了"


def test_reflection_get_reports_status_and_config(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("reflection:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    out = asyncio.run(active_bridge.reflection_get())
    assert out["status"]["live"] is True
    assert out["config"]["provider"] == "openclaw"


def test_reflection_config_set_toggles_provider(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("reflection:\n  provider: dry_run\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    out = asyncio.run(active_bridge.reflection_config_set({"provider": "openclaw"}))
    assert out["status"]["live"] is True
    assert out["config"]["provider"] == "openclaw"
    written = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("reflection")
    assert written["provider"] == "openclaw"


def test_reflection_config_set_disables(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("reflection:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    out = asyncio.run(active_bridge.reflection_config_set({"enabled": False}))
    assert out["status"]["live"] is False
    assert out["status"]["state"] == "paused"
