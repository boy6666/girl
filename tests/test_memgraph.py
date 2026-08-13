"""test_memgraph.py"""
from active import memgraph


def test_tag_theme_creates_theme_and_memory():
    g = memgraph.build_graph([("2026-08-13.md", "【爱好】主人喜欢薄荷\n")])
    labels = {n["type"]: n["label"] for n in g["nodes"]}
    assert labels["memory"] == "主人喜欢薄荷"
    assert labels["theme"] == "爱好"
    rels = {(e["rel"], e["source"]) for e in g["edges"]}
    assert ("主题", "memory:2026-08-13.md:0") in rels


def test_functional_tag_is_not_a_theme():
    g = memgraph.build_graph([("2026-08-13.md", "【状态】今天有点累\n")])
    themes = [n for n in g["nodes"] if n["type"] == "theme"]
    assert all(t["label"] not in ("状态",) for t in themes)   # 功能标签不作主题


def test_mention_you_forces_edge_to_you():
    g = memgraph.build_graph([("2026-08-13.md", "今天想起你说的话，心里一暖\n")])
    assert any(n["type"] == "you" and n["label"] == "你" for n in g["nodes"])
    assert any(e["rel"] == "关于" and e["target"] == "you:你" for e in g["edges"])


def test_about_you_tag_forces_edge():
    g = memgraph.build_graph([("2026-08-13.md", "【关于你】你怕打雷\n")])
    assert any(e["rel"] == "关于" and e["target"] == "you:你" for e in g["edges"])


def test_wiki_link_creates_theme_edge():
    g = memgraph.build_graph([("2026-08-13.md", "我们聊过[[工作]]\n")])
    assert any(n["type"] == "theme" and n["label"] == "工作" for n in g["nodes"])
    assert any(e["rel"] == "主题" and e["target"] == "theme:工作" for e in g["edges"])


def test_lexicon_classify():
    g = memgraph.build_graph([("2026-08-13.md", "路过花店那盆薄荷\n")])
    assert any(n["type"] == "theme" and n["label"] == "爱好" for n in g["nodes"])


def test_empty_sources_empty_graph():
    g = memgraph.build_graph([])
    assert g == {"nodes": [], "edges": []}


def test_theme_dedup_single_node():
    g = memgraph.build_graph(
        [("2026-08-13.md", "【爱好】a\n【爱好】b\n")])
    themes = [n for n in g["nodes"] if n["type"] == "theme"]
    assert len(themes) == 1 and themes[0]["label"] == "爱好"


def test_memory_date_from_filename():
    g = memgraph.build_graph([("2026-08-13.md", "今天看的书\n")])
    mem = [n for n in g["nodes"] if n["type"] == "memory"][0]
    assert mem["date"] == "2026-08-13"


def test_find_sources_skips_intake_and_missing(tmp_path):
    (tmp_path / "girl_workspace").mkdir()
    (tmp_path / "girl_workspace" / "memory").mkdir()
    (tmp_path / "girl_workspace" / "memory" / "reflections").mkdir()
    (tmp_path / "girl_workspace" / "memory" / "heartbeat.md").write_text("【现在】x\n", encoding="utf-8")
    (tmp_path / "girl_workspace" / "memory" / "2026-08-13.md").write_text("日记\n", encoding="utf-8")
    (tmp_path / "girl_workspace" / "USER.md").write_text("关于你\n", encoding="utf-8")
    srcs = memgraph.find_sources(tmp_path)
    names = [n for n, _ in srcs]
    assert "USER.md" in names                 # 源包含 USER.md
    assert "2026-08-13.md" in names           # 日记收录
    assert "heartbeat.md" not in names        # 摄入文件被排除
