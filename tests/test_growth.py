"""test_growth.py — 持续生长: 低频回写 GROWTH.md 的契约。
(1) 无真实积累 → 卡留空, 不现编;
(2) 有料 → 卡把「底子 + 真实相处 + 最近反思」传给 girl, 请她只追加真沉淀;
(3) inject default dry_run 零副作用; openclaw 只写 growth_in.md, sent 恒 False;
(4) should_grow 按 interval_days 低频, 未初始化/没长过 → 不问;
(5) growth_status 把 live/dry_run/paused 讲明白。
"""
from datetime import datetime, timedelta

from active import growth


def test_no_material_no_card():
    assert growth.build_growth_card(
        base_story="我 22 岁了。", reflections_note="", relations_text="") == ""


def test_card_includes_real_material_and_asks_append():
    card = growth.build_growth_card(
        base_story="我 22 岁了。", relations_text="- 他答应的事都做到了",
        reflections_note="[2026-08-17] 我也学着自己拿主意")
    assert "22 岁" in card
    assert "他答应的事" in card
    assert "学着自己" in card
    assert "追加" in card and "没长" in card     # 只请她加真沉淀, 没长就别硬写


def test_inject_defaults_to_dry_run(monkeypatch, tmp_path):
    from active import growth as g
    card = "【持续生长】后来我又…\n"
    r = g.inject_growth_card(card, "dry_run", path=tmp_path / "growth_in.md")
    assert r["dry_run"] is True and r["sent"] is False
    monkeypatch.setattr(growth, "GROWTH_INTAKE", tmp_path / "growth_in.md")
    g.inject_growth_card(card, "dry_run")
    assert not (tmp_path / "growth_in.md").exists()


def test_inject_openclaw_writes_intake_not_send(monkeypatch, tmp_path):
    from active import growth as g
    monkeypatch.setattr(g, "GROWTH_INTAKE", tmp_path / "growth_in.md")
    r = g.inject_growth_card("【持续生长】真长了一点\n", "openclaw")
    assert r["written"] is True and r["sent"] is False
    assert (tmp_path / "growth_in.md").read_text(encoding="utf-8") == "【持续生长】真长了一点\n"


def test_should_grow_respects_interval_and_low_frequency():
    base = {"initialized": True,
            "last_growth_date": (datetime.now() - timedelta(days=5)).date().isoformat()}
    assert growth.should_grow({"enabled": True, "interval_days": 3}, base) is True
    assert growth.should_grow({"enabled": True, "interval_days": 7}, base) is False


def test_should_grow_disabled_or_uninit(monkeypatch):
    assert growth.should_grow({"enabled": False, "interval_days": 1},
                           {"initialized": True, "last_growth_date": "2026-08-01"}) is False
    assert growth.should_grow({"enabled": True, "interval_days": 1},
                           {"initialized": False, "last_growth_date": None}) is False


def test_growth_status_states():
    live = growth.growth_status({"enabled": True, "provider": "openclaw", "interval_days": 2})
    assert live["live"] is True and live["state"] == "live"
    dry = growth.growth_status({"enabled": True, "provider": "dry_run"})
    assert dry["live"] is False and dry["state"] == "dry_run"
    pause = growth.growth_status({"enabled": False, "provider": "openclaw"})
    assert pause["state"] == "paused" and pause["live"] is False


# ---- bridge 路由层 ----

def test_growth_route_reports_cfg_and_status(monkeypatch, tmp_path):
    import asyncio
    from web import active_bridge as ab
    cfg = tmp_path / "config.yaml"
    cfg.write_text("growth:\n  provider: openclaw\n", encoding="utf-8")
    monkeypatch.setattr(ab, "CFG", cfg)
    out = asyncio.run(ab.growth_get())
    assert out["status"]["live"] is True
    assert out["status"]["state"] == "live"


def test_growth_trigger_no_material_is_honest(monkeypatch, tmp_path):
    import asyncio
    from web import active_bridge as ab
    # 无反思 dir + 无承诺/缺席 + 无 GROWTH.md → 没真实料 → 卡空不现编
    monkeypatch.setattr(ab.growth.reflection, "REFLECTIONS_DIR", tmp_path / "empty_reflections")
    monkeypatch.setattr(ab.growth.life_init, "_GROWTH_DEFAULT", tmp_path / "no_G.md")
    monkeypatch.setattr(ab.growth.relations, "RELATIONS_PATH", tmp_path / "none_relations.yaml")
    out = asyncio.run(ab.growth_trigger())
    assert out["card"] is None
    assert "没长" in out["note"]


def test_growth_trigger_with_real_promise_makes_card(monkeypatch, tmp_path):
    import asyncio
    from web import active_bridge as ab
    monkeypatch.setattr(ab.growth.life_init, "_GROWTH_DEFAULT", tmp_path / "G.md")
    (tmp_path / "G.md").write_text("我 22 岁了。\n", encoding="utf-8")
    monkeypatch.setattr(ab.growth.reflection, "REFLECTIONS_DIR", tmp_path / "empty_re")
    # 手造一条真实相处摘要 → 卡就带上它, 且 dry_run 零副作用
    monkeypatch.setattr(ab.growth.relations, "render_relations_summary",
                      lambda d: "他答应的事都做到了")
    out = asyncio.run(ab.growth_trigger())
    assert out["card"] and "他答应" in out["card"]
    assert out["inject"]["dry_run"] is True and out["inject"]["sent"] is False
