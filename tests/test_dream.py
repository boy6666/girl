"""test_dream.py — 非每日梦记：由头(昨天真实残余/非梦夜→None)、闸门、注入、latest、status。"""
from datetime import datetime

from active import dream, life_sim


def test_previous_day():
    assert dream.previous_day("2026-08-13") == "2026-08-12"
    assert dream.previous_day("2026-08-01") == "2026-07-31"


def test_day_residue_from_yesterday():
    content = {"buckets": {"morning": ["下班路上看夕阳"], "work": [],
                           "afternoon": [], "evening": []}}
    residue = dream.day_residue(content, "昨天我跑到她家楼下了", "2026-08-13")
    assert any("夕阳" in r or "她家楼下" in r for r in residue)


def test_day_residue_empty():
    assert dream.day_residue({"buckets": {}}, "", "2026-08-13") == []


def test_build_none_when_not_dream_night(monkeypatch):
    monkeypatch.setattr(life_sim, "_dream_night", lambda d: False)
    content = {"buckets": {"morning": ["看夕阳"]}}
    assert dream.build_dream_card(content, "", "2026-08-13",
                                  now=datetime(2026, 8, 13, 8, 0)) is None


def test_build_none_when_no_residue(monkeypatch):
    monkeypatch.setattr(life_sim, "_dream_night", lambda d: True)
    assert dream.build_dream_card({"buckets": {}}, "", "2026-08-13") is None


def test_build_card_uses_real_residue(monkeypatch):
    monkeypatch.setattr(life_sim, "_dream_night", lambda d: True)
    content = {"buckets": {"morning": ["看夕阳"], "work": ["改了一天 bug"],
                           "afternoon": [], "evening": []}}
    card = dream.build_dream_card(content, "", "2026-08-13")
    assert card is not None
    assert "昨夜由头" in card
    assert card.count("\n") >= 2


def test_should_dream_disabled():
    assert dream.should_dream({"enabled": False}, {"last_dream_date": None},
                              now=datetime(2026, 8, 13, 9, 0), wake="08:00") is False


def test_should_dream_before_wake():
    assert dream.should_dream({"enabled": True}, {"last_dream_date": None},
                              now=datetime(2026, 8, 13, 7, 0), wake="08:00") is False


def test_should_dream_after_wake():
    assert dream.should_dream({"enabled": True}, {"last_dream_date": None},
                              now=datetime(2026, 8, 13, 9, 0), wake="08:00") is True


def test_should_dream_already_marked():
    assert dream.should_dream({"enabled": True}, {"last_dream_date": "2026-08-13"},
                              now=datetime(2026, 8, 13, 9, 0), wake="08:00") is False


def test_mark_dream():
    assert dream.mark_dream({}, "2026-08-13")["last_dream_date"] == "2026-08-13"


def test_inject_dry_run_no_write(tmp_path):
    r = dream.inject_dream_card("【日期】2026-08-13", "dry_run", path=tmp_path / "x.md")
    assert r["dry_run"] is True and r["sent"] is False
    assert not (tmp_path / "x.md").exists()


def test_inject_openclaw_writes_not_sends(tmp_path):
    p = tmp_path / "dream_in.md"
    r = dream.inject_dream_card("【日期】2026-08-13", "openclaw", path=p)
    assert r["sent"] is False and r["written"] is True
    assert p.read_text(encoding="utf-8") == "【日期】2026-08-13\n"


def test_latest_dream(monkeypatch, tmp_path):
    monkeypatch.setattr(dream, "DREAMS_DIR", tmp_path)
    (tmp_path / "2026-08-12.md").write_text("梦见夕阳\n", encoding="utf-8")
    latest = dream.latest_dream()
    assert latest["date"] == "2026-08-12"
    assert latest["first_line"] == "梦见夕阳"


def test_dream_status():
    assert dream.dream_status({"enabled": True, "provider": "openclaw"})["live"] is True
    assert dream.dream_status({"enabled": False})["state"] == "paused"
    assert dream.dream_status({"enabled": True, "provider": "dry_run"})["state"] == "dry_run"
