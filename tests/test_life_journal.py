from active import life_journal as lj


def test_append_and_recent(tmp_path):
    p = tmp_path / "j.md"
    lj.append_entry("2026-08-10", "前天去看海。", p)
    lj.append_entry("2026-08-11", "今天散步遇到一只猫。", p)
    assert lj.last_entry_date(p) == "2026-08-11"
    rec = lj.recent_entries(p, 2)
    assert rec == ["今天散步遇到一只猫。", "前天去看海。"]


def test_empty(tmp_path):
    assert lj.recent_entries(tmp_path / "none.md") == []
    assert lj.last_entry_date(tmp_path / "none.md") is None


def test_recent_entries_from_text():
    txt = "## 2026-08-10\n前天去看海。\n## 2026-08-11\n今天遇到猫。\n"
    assert lj.recent_entries_from_text(txt, 1) == ["今天遇到猫。"]
