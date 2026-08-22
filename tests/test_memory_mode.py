"""memory_mode — 记忆·检索盐度旋钮（eager|auto|cautious 三档）。
渲染 §记忆 分块进 PROACTIVE_INTAKE.md 的 BEGIN/END 之间，只动那一段。
"""
from active import memory_mode as mm


def test_load_default_auto(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("memory:\n  recall_mode: eager\n", encoding="utf-8")
    assert mm.load_mode(cfg) == "eager"


def test_load_invalid_falls_back_auto(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("memory:\n  recall_mode: junk\n", encoding="utf-8")
    assert mm.load_mode(cfg) == "auto"
    assert mm.load_mode(tmp_path / "nope.yaml") == "auto"   # 缺文件→auto
    cfg.write_text("personality:\n  sweetness: 65\n", encoding="utf-8")
    assert mm.load_mode(cfg) == "auto"                       # 无 recall_mode→auto


def test_render_block_contains_mode_and_guidance():
    for mode in mm.MODES:
        b = mm.render_block(mode)
        assert f"recall_mode = {mode}" in b
        assert mm.GUIDANCE[mode] in b
        assert mm._BEGIN in b and mm._END in b
        assert b.count(mm._BEGIN) == 1 and b.count(mm._END) == 1
        # 闭合完整（不出现解包成元组的残留）
        assert b.count("(") == b.count(")")


def test_apply_replaces_previous_block(tmp_path):
    intake = tmp_path / "PROACTIVE_INTAKE.md"
    intake.write_text("# P\n正文\n" + mm.render_block("auto") + "\n尾\n",
                      encoding="utf-8")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("memory:\n  recall_mode: eager\n", encoding="utf-8")
    b = mm.apply_to_intake(intake_path=intake, cfg_path=cfg)
    assert b and "recall_mode = eager" in b
    text = intake.read_text(encoding="utf-8")
    assert text.count(mm._BEGIN) == 1 and text.count(mm._END) == 1
    assert "recall_mode = eager" in text
    assert text.startswith("# P") and text.rstrip().endswith("尾")  # 首尾原样


def test_apply_appends_when_no_block(tmp_path):
    intake = tmp_path / "PROACTIVE_INTAKE.md"
    intake.write_text("# P\n尾部\n", encoding="utf-8")
    assert mm.apply_to_intake(intake_path=intake)
    text = intake.read_text(encoding="utf-8")
    assert text.count(mm._BEGIN) == 1
    assert "尾部" in text.split(mm._BEGIN)[0]               # 原正文留在块前


def test_apply_missing_file_noop(tmp_path):
    assert mm.apply_to_intake(intake_path=tmp_path / "nope.md") is None
    assert not (tmp_path / "nope.md").exists()               # 不凭空创建


def test_apply_partial_marker_noop(tmp_path):
    # 只开了 BEGIN 没 END → 不认作已有分块，也不半截替换
    intake = tmp_path / "p.md"
    intake.write_text("# P\n" + mm._BEGIN + "\n正文\n", encoding="utf-8")
    assert mm.apply_to_intake(intake_path=intake) is not None
    text = intake.read_text(encoding="utf-8")
    assert text.count(mm._BEGIN) == 2  # 旧半截 + 新一整块，旧半截原样躺着


def test_load_mode_and_render_agree(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("memory:\n  recall_mode: cautious\n", encoding="utf-8")
    assert f"recall_mode = {mm.load_mode(cfg)}" in mm.render_block(mm.load_mode(cfg))
