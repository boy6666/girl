from active import injector


def test_dry_run_never_sends():
    r = injector.inject_motivation("【现在】在睡觉")
    assert r["sent"] is False
    assert r["dry_run"] is True
    assert r["card"] == "【现在】在睡觉"


def test_openclaw_writes_card_not_sends(tmp_path):
    hp = tmp_path / "memory" / "heartbeat.md"
    r = injector.inject_motivation("【现在】在睡觉", provider="openclaw",
                                   heartbeat_path=hp)
    assert r["sent"] is False          # 写文件≠发微信
    assert r["written"] is True
    assert hp.read_text(encoding="utf-8") == "【现在】在睡觉\n"
