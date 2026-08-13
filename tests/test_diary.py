"""test_diary.py — 叙事日记：造卡(真实取料/留白)、闸门、注入(dry_run/openclaw)、latest、status。"""
from datetime import datetime
from pathlib import Path

from active import diary


def test_build_card_uses_real_highlights():
    content = {"buckets": {"morning": ["晨跑"], "work": ["写了个模块"],
                           "afternoon": [], "evening": []}}
    card = diary.build_diary_card(content, "", "2026-08-13",
                                  now=datetime(2026, 8, 13, 21, 0))
    assert "【日期】2026-08-13" in card
    assert "晨跑" in card or "写了个模块" in card
    assert "你的私人日记" in card


def test_build_card_blank_keeps_true():
    card = diary.build_diary_card({"buckets": {}}, "", "2026-08-13",
                                  now=datetime(2026, 8, 13, 21, 0))
    assert "平平淡淡" in card      # 留白，不编事件


def test_should_diary_disabled():
    assert diary.should_diary({"enabled": False}, {"last_diary_date": None},
                              now=datetime(2026, 8, 13, 23, 0), bedtime="23:00") is False


def test_should_diary_before_bedtime():
    assert diary.should_diary({"enabled": True}, {"last_diary_date": None},
                              now=datetime(2026, 8, 13, 22, 0), bedtime="23:00") is False


def test_should_diary_after_bedtime():
    assert diary.should_diary({"enabled": True}, {"last_diary_date": None},
                              now=datetime(2026, 8, 13, 23, 30), bedtime="23:00") is True


def test_should_diary_already_marked():
    assert diary.should_diary({"enabled": True}, {"last_diary_date": "2026-08-13"},
                              now=datetime(2026, 8, 13, 23, 30), bedtime="23:00") is False


def test_mark_diary():
    st = {}
    assert diary.mark_diary(st, "2026-08-13")["last_diary_date"] == "2026-08-13"


def test_inject_dry_run_no_write(tmp_path):
    r = diary.inject_diary_card("【日期】2026-08-13", "dry_run",
                                path=tmp_path / "d.md")
    assert r["dry_run"] is True and r["sent"] is False
    assert not (tmp_path / "d.md").exists()


def test_inject_openclaw_writes_not_sends(tmp_path):
    p = tmp_path / "diary_in.md"
    r = diary.inject_diary_card("【日期】2026-08-13", "openclaw", path=p)
    assert r["sent"] is False and r["written"] is True
    assert p.read_text(encoding="utf-8") == "【日期】2026-08-13\n"


def test_latest_diary(monkeypatch, tmp_path):
    monkeypatch.setattr(diary, "DIARY_DIR", tmp_path)
    (tmp_path / "2026-08-12.md").write_text("第一条\n", encoding="utf-8")
    (tmp_path / "2026-08-13.md").write_text("今天更懂你了\n", encoding="utf-8")
    latest = diary.latest_diary()
    assert latest["date"] == "2026-08-13"
    assert latest["first_line"] == "今天更懂你了"


def test_latest_diary_none(monkeypatch, tmp_path):
    monkeypatch.setattr(diary, "DIARY_DIR", tmp_path)
    assert diary.latest_diary() is None


def test_diary_status_live_paused_dryrun(tmp_path):
    assert diary.diary_status({"enabled": True, "provider": "openclaw"})["live"] is True
    assert diary.diary_status({"enabled": False})["state"] == "paused"
    assert diary.diary_status({"enabled": True, "provider": "dry_run"})["state"] == "dry_run"
