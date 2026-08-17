from active import relations as r


def test_default_is_empty():
    d = r.DEFAULT
    assert d["promises"] == [] and d["absences"] == []


def test_add_promise_and_open(tmp_path):
    d = r.add_promise({}, "周末陪我看电影", "2026-08-17")
    assert d["promises"][0]["status"] == "pending"
    assert r.open_promises(d) == ["周末陪我看电影"]


def test_mark_kept_and_broken(tmp_path):
    d = {"promises": [{"text": "早睡", "made_on": "2026-08-16", "status": "pending"}]}
    d = r.mark_kept(d, 0, "2026-08-17")
    assert d["promises"][0]["status"] == "kept"
    d = r.mark_broken(d, 0, "2026-08-18")
    assert d["promises"][0]["status"] == "broken"


def test_local_lifecycle_preserves_other(tmp_path):
    p = tmp_path / "relations.yaml"
    p.write_text("absences:\n  - note: 周三没找我吃饭\n    at: '2026-08-15'\n",
                encoding="utf-8")
    d = r.load(p)
    d = r.add_absence(d, "今天也没回消息", "2026-08-17")
    r.save(d, p)
    assert "今天也没回消息" in r.recent_absences(r.load(p))
    assert "周三没找我吃饭" in r.recent_absences(d)


def test_render_summary_only_real_facts():
    d = {"promises": [{"text": "会认真回我", "made_on": "2026-08-10", "status": "broken"}],
         "absences": [{"note": "连着两天没理我", "at": "2026-08-16"}]}
    txt = r.render_relations_summary(d)
    assert "会认真回我" in txt and "没理我" in txt


def test_render_summary_empty_gives_empty():
    assert r.render_relations_summary({"promises": [], "absences": []}) == ""
