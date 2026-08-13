"""test_reflection.py"""
from datetime import datetime
from pathlib import Path

from active import reflection, life_journal, state_store


def _content(today=("下午路过花店，那盆薄荷我想带回家",)):
    return {"buckets": {"evening": list(today)}}


def test_build_card_has_date_and_life():
    c = reflection.build_reflection_card(
        _content(), "", "2026-08-13", now=datetime(2026, 8, 13, 22, 0))
    assert "【日期】2026-08-13" in c
    assert "那盆薄荷我想带回家" in c
    assert "不发给主人看" in c       # 请求卡是内化，不是发消息


def test_build_card_includes_today_journal_self():
    journal = "\n## 2026-08-13\n今天有点累，但心里暖。\n"
    c = reflection.build_reflection_card(
        {}, journal, "2026-08-13", now=datetime(2026, 8, 13, 22, 0))
    assert "今天有点累，但心里暖" in c


def test_build_card_blank_when_nothing_real():
    c = reflection.build_reflection_card(
        {}, "", "2026-08-13", now=datetime(2026, 8, 13, 22, 0))
    assert "平平淡淡" in c           # 无素材留白，不现编


def test_entry_for_date_returns_body_only_for_that_day():
    text = "\n## 2026-08-12\n昨天的事。\n## 2026-08-13\n今天的事。\n"
    assert life_journal.entry_for_date(text, "2026-08-13") == "今天的事。"
    assert life_journal.entry_for_date(text, "2026-08-11") == ""


def test_should_reflect_gate():
    assert not reflection.should_reflect(
        {"enabled": False, "window": "22:00"}, state_store.default_state(),
        now=datetime(2026, 8, 13, 23, 0))
    assert not reflection.should_reflect(
        {"enabled": True, "window": "22:00"}, state_store.default_state(),
        now=datetime(2026, 8, 13, 21, 59))
    assert reflection.should_reflect(
        {"enabled": True, "window": "22:00"}, state_store.default_state(),
        now=datetime(2026, 8, 13, 22, 0))
    st = {"last_reflection_date": "2026-08-13"}
    assert not reflection.should_reflect(
        {"enabled": True, "window": "22:00"}, st,
        now=datetime(2026, 8, 13, 23, 0))
    assert reflection.should_reflect(
        {"enabled": True, "window": "22:00"}, st,
        now=datetime(2026, 8, 14, 22, 30))   # 跨天重置


def test_should_reflect_bad_window_falls_back_to_default():
    assert reflection.should_reflect(
        {"enabled": True, "window": "bad"}, state_store.default_state(),
        now=datetime(2026, 8, 13, 23, 0))    # 坏配置回退 22:00 → 已过即触发


def test_inject_dry_run_no_side_effect(tmp_path):
    p = tmp_path / "reflect.md"
    r = reflection.inject_reflection_card("【日期】x", "dry_run", path=p)
    assert r["dry_run"] is True and r["sent"] is False
    assert not p.exists()                     # dry_run 不碰文件


def test_inject_openclaw_writes_not_sends(tmp_path):
    p = tmp_path / "reflect.md"
    r = reflection.inject_reflection_card("【日期】2026-08-13", "openclaw", path=p)
    assert r["sent"] is False and r["written"] is True
    assert p.read_text(encoding="utf-8") == "【日期】2026-08-13\n"


def test_mark_reflected():
    st = {}
    assert reflection.mark_reflected(st, "2026-08-13")["last_reflection_date"] == "2026-08-13"


def test_latest_reflection(monkeypatch, tmp_path):
    monkeypatch.setattr(reflection, "REFLECTIONS_DIR", tmp_path)
    assert reflection.latest_reflection() is None
    (tmp_path / "2026-08-12.md").write_text("昨天\n", encoding="utf-8")
    (tmp_path / "2026-08-13.md").write_text("今天更懂你了\n", encoding="utf-8")
    got = reflection.latest_reflection()
    assert got["date"] == "2026-08-13"
    assert got["first_line"] == "今天更懂你了"
