from active import injector


def test_dry_run_never_sends():
    r = injector.inject_motivation("【现在】在睡觉")
    assert r["sent"] is False
    assert r["dry_run"] is True
    assert r["card"] == "【现在】在睡觉"
