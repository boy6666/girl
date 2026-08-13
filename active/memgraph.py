"""memgraph.py — 记忆图谱：把她记忆文件抽成 {nodes, edges}（读侧投影）。

只读/抽/拼：零发送、零写记忆、零出网。启发式、确定性、可测。
社科：展示 McAdams 叙事同一性的产物——碎片如何编成"关于你和她的故事"。
不现编：主题词表只做分类、不做内容；无命中不硬塞主题。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 主题词表：小型、诚实、只归不造。命中多处取首；无命中不贴主题。
THEME_WORDS = {
    "爱好": ["喜欢", "爱", "游戏", "音乐", "电影", "书", "咖啡", "薄荷"],
    "工作": ["工作", "上班", "加班", "项目"],
    "家人": ["家人", "妈妈", "爸爸"],
    "健康": ["累", "睡", "病", "疼"],
    "梦": ["梦", "梦见"],
    "情绪": ["开心", "难过", "失落", "暖", "心疼", "担心"],
    "地点": ["花店", "公园", "公司", "路上"],
}

# about-you 命中词（提及你 → 必连 you）
YOU_WORDS = ["你", "主人", "他", "我们"]

# 功能性标签：不作主题节点，只作标记（如此刻/状态/日期）
_FUNCTIONAL_TAGS = {"此刻", "今天", "昨天", "状态", "现在", "日期", "我的一天", "今天的生活"}

_TAG_HEAD = re.compile(r"^【([^】]+)】\s*(.*)$")
_LINK = re.compile(r"\[\[([^\]]+)\]\]")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _theme_for(text: str) -> str | None:
    for th, words in THEME_WORDS.items():
        for w in words:
            if w in text:
                return th
    return None


def _mention_you(text: str) -> bool:
    return any(w in text for w in YOU_WORDS)


def _file_date(name: str) -> str:
    m = _DATE.search(name)
    return m.group(1) if m else ""


def build_graph(sources: list[tuple[str, str]]) -> dict:
    """sources: [(name, text), ...] → {nodes, edges}。纯函数、确定性。"""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    mem_i = 0

    def _add(type_: str, label: str) -> str:
        nid = f"{type_}:{label}"
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": type_, "label": label,
                          "date": "", "text": ""}
        return nid

    for name, text in sources:
        date = _file_date(name)
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            m = _TAG_HEAD.match(line)
            if m:
                tag, body = m.group(1).strip(), m.group(2).strip()
            else:
                tag, body = "", line
            if not body and not _LINK.search(line):
                continue
            mnid = f"memory:{name}:{mem_i}"
            mem_i += 1
            nodes[mnid] = {"id": mnid, "type": "memory", "label": body or line,
                           "date": date, "text": body or line}
            theme = tag if tag in THEME_WORDS else _theme_for(body or line)
            if theme:
                tid = _add("theme", theme)
                edges.append({"source": mnid, "target": tid, "rel": "主题"})
                edges.append({"source": tid, "target": mnid, "rel": "含"})
            if _mention_you(body or line) or tag == "关于你":
                yid = _add("you", "你")
                edges.append({"source": mnid, "target": yid, "rel": "关于"})
            for lnk in _LINK.findall(line):
                lid = _add("theme", lnk.strip())
                edges.append({"source": mnid, "target": lid, "rel": "主题"})
                edges.append({"source": lid, "target": mnid, "rel": "含"})
    return {"nodes": list(nodes.values()), "edges": edges}


def find_sources(root: Path | None = None) -> list[tuple[str, str]]:
    """收集 5 类记忆源为 [(name, text), ...]；缺失/摄入文件静默跳过。"""
    root = root or ROOT
    out: list[tuple[str, str]] = []
    candidates = [
        root / "girl_workspace" / "USER.md",
        root / "girl_workspace" / "MEMORY.md",
        *[p for p in (root / "girl_workspace" / "memory").glob("*.md")
          if _DATE.search(p.name)],                       # 只收日期日记，排除 heartbeat/reflect
        *sorted((root / "girl_workspace" / "memory" / "reflections").glob("*.md")),
        root / "data" / "life_journal.md",
    ]
    for p in candidates:
        try:
            if p.is_file():
                out.append((p.name, p.read_text(encoding="utf-8")))
        except OSError:
            pass
    return out
