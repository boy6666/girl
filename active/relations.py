"""relations.py — 承诺/缺席持久化(关系侧资源)。

只记真实发生过的事: 主人答应过什么(promises)、哪些没兑现/缺席(absences)。
与 life_content 同理: 代码不现编, 默认空, 由相处数据/Web 填进来。
单一出口: 这里只读写文件 / 返回摘要, 不真发微信。
"""
import yaml
from pathlib import Path

RELATIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "relations.yaml"

DEFAULT = {"promises": [], "absences": []}
_PROMISE_STATUS = ("pending", "kept", "broken")


def load(path: Path = RELATIONS_PATH) -> dict:
    d = {"promises": [], "absences": []}
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        d["promises"] = [p for p in data.get("promises", []) if p.get("text")]
        d["absences"] = [a for a in data.get("absences", []) if a.get("note")]
    return d


def save(d: dict, path: Path = RELATIONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False),
                  encoding="utf-8")


def add_promise(d: dict, text: str, made_on: str) -> dict:
    d.setdefault("promises", []).append({"text": text, "made_on": made_on, "status": "pending"})
    return d


def mark_kept(d: dict, index: int, on: str) -> dict:
    if 0 <= index < len(d["promises"]):
        d["promises"][index]["status"] = "kept"
        d["promises"][index]["kept_on"] = on
    return d


def mark_broken(d: dict, index: int, on: str) -> dict:
    if 0 <= index < len(d["promises"]):
        d["promises"][index]["status"] = "broken"
        d["promises"][index]["broken_on"] = on
    return d


def add_absence(d: dict, note: str, at: str) -> dict:
    d.setdefault("absences", []).append({"note": note, "at": at})
    return d


def open_promises(d: dict) -> list:
    return [p["text"] for p in d["promises"] if p.get("status") == "pending"]


def broken_promises(d: dict) -> list:
    return [p["text"] for p in d["promises"] if p.get("status") == "broken"]


def recent_absences(d: dict, n: int = 3) -> list:
    return [a["note"] for a in d["absences"][-n:]][::-1]


def render_relations_summary(d: dict) -> str:
    """把真实的承诺/缺席压成一两行; 没有真实事实 → ''(不现编)。"""
    parts = []
    broken = broken_promises(d)
    if broken:
        parts.append("他没兑现的:" + "、".join(broken))
    ab = recent_absences(d)
    if ab:
        parts.append("这几天他缺席:" + "、".join(ab))
    return "，".join(parts)
