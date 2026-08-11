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
