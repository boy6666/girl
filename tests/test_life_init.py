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
