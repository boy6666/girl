from active import life_content as lc, life_grower as lg


def _content():
    return {"habits": ["喜欢猫"], "favorites": {"food": "咖啡"},
            "schedule": {"wake": 7},
            "buckets": {"morning": ["晨跑"], "work": ["写代码"],
                        "afternoon": ["散步"], "evening": ["按时睡"]}}


def test_dry_run_uses_content_and_returns_text():
    txt = lg.grow_today(_content(), "", "2026-08-11", provider="dry_run", seed=1)
    assert isinstance(txt, str) and len(txt) > 10


def test_dry_run_deterministic():
    a = lg.grow_today(_content(), "", "2026-08-11", provider="dry_run", seed=7)
    b = lg.grow_today(_content(), "", "2026-08-11", provider="dry_run", seed=7)
    assert a == b
