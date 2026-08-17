from active import life_grower as lg


def _filled_content():
    return {"habits": ["喜欢猫"], "favorites": {"food": "咖啡"},
            "schedule": {"wake": 7},
            "buckets": {"morning": ["晨跑"], "work": ["写代码"],
                        "afternoon": ["散步"], "evening": ["按时睡"]}}


def _empty_content():
    return {"habits": [], "favorites": {}, "schedule": {"wake": 7},
            "buckets": {"morning": [], "work": [], "afternoon": [], "evening": []}}


def test_dry_run_uses_filled_content_and_returns_text():
    txt = lg.grow_today(_filled_content(), "", "2026-08-11", provider="dry_run", seed=1)
    assert isinstance(txt, str) and len(txt) > 10


def test_dry_run_does_not_fabricate_when_empty():
    txt = lg.grow_today(_empty_content(), "", "2026-08-11", provider="dry_run", seed=1)
    assert "没" in txt or "平淡" in txt  # 无内容则平淡留白，不硬造


def test_dry_run_deterministic():
    a = lg.grow_today(_filled_content(), "", "2026-08-11", provider="dry_run", seed=7)
    b = lg.grow_today(_filled_content(), "", "2026-08-11", provider="dry_run", seed=7)
    assert a == b


def test_motivation_card_adds_xinshi_only_when_real(monkeypatch):
    from active import motivation
    rel = {"promises": [{"text": "说好周三陪我", "made_on": "2026-08-10",
                        "status": "broken"}],
           "absences": [{"note": "这两天没怎么理我", "at": "2026-08-16"}]}
    card = motivation.build_motivation_card(
        {"energy": 60, "mood": 0.1}, {}, "", "2026-08-17",
        emoji_mode="off", relations=rel)
    assert "【心事】" in card and "这两天没怎么理我" in card


def test_motivation_card_omits_xinshi_when_none():
    from active import motivation
    card = motivation.build_motivation_card(
        {"energy": 60, "mood": 0.1}, {}, "", "2026-08-17",
        emoji_mode="off", relations={"promises": [], "absences": []})
    assert "【心事】" not in card
