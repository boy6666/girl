"""test_active_bridge.py — 自动主动窗口的注入契约：读 inject_provider 配置。
默认 dry_run 无副作用；翻成 openclaw 时只写心跳文件、sent 恒 False（单一出口）。
"""
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
