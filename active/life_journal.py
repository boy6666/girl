"""life_journal.py — 生活日志 data/life_journal.md（agent 生长，读+append）。"""
from pathlib import Path

JOURNAL_PATH = Path(__file__).resolve().parents[1] / "data" / "life_journal.md"


def read_journal(path: Path = JOURNAL_PATH) -> str:
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def append_entry(day: str, text: str, path: Path = JOURNAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## {day}\n{text}\n")


def _parse_entries(text: str) -> list[tuple[str, str]]:
    entries = []   # (date, body) in file order
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            entries.append((cur, ""))
        elif cur is not None and line.strip():
            entries[-1] = (entries[-1][0], entries[-1][1] + line.strip() + "\n")
    return entries


def recent_entries(path: Path = JOURNAL_PATH, n: int = 3) -> list[str]:
    return recent_entries_from_text(read_journal(path), n)


def recent_entries_from_text(text: str, n: int = 1) -> list[str]:
    bodies = [b.strip() for _, b in _parse_entries(text)]
    return bodies[-n:][::-1]   # 最新在前


def last_entry_date(path: Path = JOURNAL_PATH) -> str | None:
    entries = _parse_entries(read_journal(path))
    return entries[-1][0] if entries else None


def entry_for_date(text: str, day: str) -> str:
    """返回指定日期的日志正文；没有该日条目 → ''。"""
    for d, b in _parse_entries(text):
        if d == day:
            return b.strip()
    return ""
