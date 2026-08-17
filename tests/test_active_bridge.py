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


# ---- 作息 / 日记 / 梦（夜间记忆链路） ----

def test_circadian_get_returns_schedule(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("circadian:\n  bedtime: \"23:00\"\n  wake: \"08:00\"\n",
                   encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    monkeypatch.setattr(active_bridge.agent_admin, "latest_user_contact", lambda: None)
    out = asyncio.run(active_bridge.circadian_get())
    assert out["schedule"]["bedtime"] == "23:00"
    assert out["schedule"]["wake"] == "08:00"
    assert out["config"]["max_shift_min"] == 240


def test_circadian_get_late_shift(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("circadian:\n  bedtime: \"23:00\"\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    contact = {"ts": "2026-08-13T01:30:00", "text": "还在陪你聊"}
    monkeypatch.setattr(active_bridge.agent_admin, "latest_user_contact",
                        lambda: contact)
    out = asyncio.run(active_bridge.circadian_get())
    assert out["schedule"]["bedtime"] == "01:30"
    assert out["inputs"]["last_contact_clock"] == 1 * 60 + 30


def test_circadian_get_wind_down(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("circadian:\n  bedtime: \"23:00\"\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    # 今天的一条“早睡”真话（今天午后，不在深夜带 → 晚睡不抢）→ wind_down
    from datetime import date
    ts = f"{date.today().isoformat()}T15:00:00"
    contact = {"ts": ts, "text": "今天好累 我先睡了"}
    monkeypatch.setattr(active_bridge.agent_admin, "latest_user_contact",
                        lambda: contact)
    out = asyncio.run(active_bridge.circadian_get())
    assert out["inputs"]["wind_down"] is True
    assert out["schedule"]["bedtime"] == "21:00"


def test_diary_config_set_toggles_provider(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("diary:\n  provider: dry_run\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    out = asyncio.run(active_bridge.diary_config_set({"provider": "openclaw"}))
    assert out["status"]["live"] is True
    written = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("diary")
    assert written["provider"] == "openclaw"


def test_diary_get_reports_status_and_latest(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("diary:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    d = tmp_path / "diary"; d.mkdir()
    (d / "2026-08-13.md").write_text("今天更懂你了\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge.diary, "DIARY_DIR", d)
    out = asyncio.run(active_bridge.diary_get())
    assert out["status"]["live"] is True
    assert out["latest"]["date"] == "2026-08-13"


def test_diary_trigger_dry_run(monkeypatch):
    import asyncio
    monkeypatch.setattr(active_bridge, "_diary_cfg", lambda: {"enabled": True, "provider": "dry_run"})
    out = asyncio.run(active_bridge.diary_trigger())
    assert out["card"]
    assert out["inject"]["dry_run"] is True and out["inject"]["sent"] is False


def test_dream_config_set_disables(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    cfg.write_text("dream:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    out = asyncio.run(active_bridge.dream_config_set({"enabled": False}))
    assert out["status"]["state"] == "paused"


def test_dream_trigger_returns_none_if_no_residue(monkeypatch):
    import asyncio
    monkeypatch.setattr(active_bridge, "_dream_cfg", lambda: {"enabled": True, "provider": "dry_run"})
    monkeypatch.setattr(active_bridge.dream.life_sim, "_dream_night", lambda d: True)
    monkeypatch.setattr(active_bridge.life_content, "load_content", lambda *a: {"buckets": {}})
    out = asyncio.run(active_bridge.dream_trigger())
    assert out["card"] is None      # 无真实残余 → 不做梦


def test_dream_trigger_dry_run_card(monkeypatch):
    import asyncio
    monkeypatch.setattr(active_bridge, "_dream_cfg", lambda: {"enabled": True, "provider": "dry_run"})
    monkeypatch.setattr(active_bridge.dream.life_sim, "_dream_night", lambda d: True)
    content = {"buckets": {"morning": ["看夕阳"], "work": [],
                           "afternoon": [], "evening": []}}
    monkeypatch.setattr(active_bridge.life_content, "load_content", lambda *a: content)
    out = asyncio.run(active_bridge.dream_trigger())
    assert out["card"] and "昨夜由头" in out["card"]
    assert out["inject"]["dry_run"] is True and out["inject"]["sent"] is False


# ---- 自动初始化 ----

def _init_cfg_file(cfg, age="22"):
    cfg.write_text(f"setup:\n  girl:\n    name: 小语\n    age: '{age}'\n",
                  encoding="utf-8")


def test_init_status_honest_when_no_growth(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    _init_cfg_file(cfg)
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    monkeypatch.setattr(active_bridge.life_init, "_GROWTH_DEFAULT",
                      tmp_path / "GROWTH.md")
    out = asyncio.run(active_bridge.init_status())
    assert out["initialized"] is False
    assert out["target_age"] == 22


def test_init_trigger_dry_run_no_file_side_effect(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    _init_cfg_file(cfg, age="22")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    monkeypatch.setattr(active_bridge, "_init_cfg", lambda: {"provider": "dry_run"})
    monkeypatch.setattr(active_bridge.life_init, "_INTAKE_DEFAULT",
                      tmp_path / "INIT_INTAKE.md")
    out = asyncio.run(active_bridge.init_status_trigger())
    assert out["inject"]["dry_run"] is True
    assert out["target_age"] == 22 and "22 岁" in out["card"]
    assert not (tmp_path / "INIT_INTAKE.md").exists()   # dry_run 零副作用


def test_init_trigger_openclaw_writes_intake(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    _init_cfg_file(cfg, age="22")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    monkeypatch.setattr(active_bridge, "_init_cfg", lambda: {"provider": "openclaw"})
    monkeypatch.setattr(active_bridge.life_init, "_INTAKE_DEFAULT",
                      tmp_path / "INIT_INTAKE.md")
    out = asyncio.run(active_bridge.init_status_trigger())
    assert out["inject"]["written"] is True and out["inject"]["sent"] is False
    assert (tmp_path / "INIT_INTAKE.md").is_file()


def test_init_trigger_no_target_age_is_honest(monkeypatch, tmp_path):
    import asyncio
    cfg = tmp_path / "config.yaml"
    _init_cfg_file(cfg, age="")
    monkeypatch.setattr(active_bridge, "CFG", cfg)
    monkeypatch.setattr(active_bridge, "_init_cfg", lambda: {"provider": "dry_run"})
    out = asyncio.run(active_bridge.init_status_trigger())
    assert out["card"] is None
    assert "年龄" in out["note"]
