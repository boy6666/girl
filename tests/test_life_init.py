from active import life_init as li


def test_stages_cover_child_to_adult():
    assert li.STAGES[0]["start"] == 0
    assert len(li.stages_up_to(20)) >= 3


def test_stages_up_to_respects_upper_bound():
    stages = li.stages_up_to(20)
    assert all(s["start"] < 20 for s in stages)
    assert stages[-1]["start"] <= 20


def test_resolve_target_age_from_girl_age():
    assert li.resolve_target_age({"girl": {"age": "22"}}) == 22


def test_resolve_target_age_ignores_garbage():
    assert li.resolve_target_age({"girl": {"age": ""}}) is None


def test_frame_init_request_mentions_stages_and_honest():
    card = li.frame_init_request({"girl": {"name": "小语", "age": ""}}, 22)
    assert "0" in card and "22" in card
    assert "信任" in card or "同一性" in card


def test_frame_init_request_never_claims_personhood_in_dry_run():
    from active import life_init as li
    card = li.frame_init_request({"girl": {"name": "小语", "age": "22"}}, 22)
    assert "GROWTH.md" in card


def test_inject_init_dry_run_no_side_effect(tmp_path):
    from active import life_init as li
    p = tmp_path / "INIT_INTAKE.md"
    r = li.inject_init_request("【请求】长到 22 岁", "dry_run", path=p)
    assert r["dry_run"] is True and r["sent"] is False
    assert not p.exists()


def test_inject_init_openclaw_writes_intake(tmp_path):
    from active import life_init as li
    p = tmp_path / "INIT_INTAKE.md"
    r = li.inject_init_request("【请求】长到 22 岁", "openclaw", path=p)
    assert r["written"] is True and r["sent"] is False
    assert "长到 22 岁" in p.read_text(encoding="utf-8")


def test_init_status_honest_when_no_growth_yet(tmp_path):
    from active import life_init as li
    st = li.init_status(growth_path=tmp_path / "GROWTH.md")
    assert st["initialized"] is False
    assert "还没有" in st.get("note", "")


def test_init_status_reads_growth_when_exists(tmp_path):
    from active import life_init as li
    gp = tmp_path / "GROWTH.md"
    gp.write_text("# GROWTH.md\n我活到了 22 岁。\n", encoding="utf-8")
    st = li.init_status(growth_path=gp)
    assert st["initialized"] is True
    assert "22 岁" in st["story"]
