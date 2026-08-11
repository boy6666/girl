from active import life_content as lc


def test_defaults_loaded(tmp_path):
    c_ = lc.load_content(tmp_path / "none.yaml")
    assert c_["schedule"]["wake"] == 7
    assert len(c_["buckets"]["morning"]) >= 1
    assert isinstance(c_["habits"], list)


def test_load_merges_user_bucket(tmp_path):
    p = tmp_path / "life_content.yaml"
    p.write_text("buckets:\n  morning: [\"自定义晨间\"]\n", encoding="utf-8")
    c_ = lc.load_content(p)
    assert c_["buckets"]["morning"] == ["自定义晨间"]
    assert len(c_["buckets"]["work"]) >= 1  # 未配置的时段仍用默认


def test_save_roundtrip(tmp_path):
    p = tmp_path / "life_content.yaml"
    content = lc.load_content()
    content["habits"].append("喜欢下雨天")
    lc.save_content(content, p)
    assert "喜欢下雨天" in lc.load_content(p)["habits"]
