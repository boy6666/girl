"""scheduler.py — E3 自定时刻（爱语「时间自决」协议移植）。

她亲口排「下次几点」→ 写 girl_workspace/memory/schedule_in.md → 收进 data/schedule.json
→ 到点 pop 一间，走时刻路径开窗（凌驾渴望阈值与深夜软窗；双钥匙 OR，阈值路径照走）。

协议（爱语 §3.2/3.3 移植，熟读即清）：
  - 每次开窗卡片尾部带「下次几点」追问（见 motivation 的 schedule 尾段）
  - 她只回两种：绝对 HH:MM（如 20:00）或 相对 数字+单位(s|min|h)
  - 一次一换：到点开一次窗，用完即焚（pop_due）
  - pending 上限 schedule_cap（默认 24）；超出的只留最近 cap 条
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_IN = ROOT / "girl_workspace" / "memory" / "schedule_in.md"
SCHEDULE_STORE = ROOT / "data" / "schedule.json"

_ABS_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$", re.ASCII)
_REL_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|min|h|秒|分钟|小时)\s*$")
_UNITS = {"s": "seconds", "秒": "seconds",
          "min": "minutes", "分钟": "minutes",
          "h": "hours", "小时": "hours"}

INBOX_HEADER = (
    "<!-- 主动·时间自决摄入（E3）：她亲口排的「下次几点」，状态机到点开窗。熟读即清。 -->\n"
    "<!-- 只认两种格式：HH:MM（如 20:00）或 数字+单位（如 30min / 1h / 90s）。 -->\n"
)


# ---------- 解析 ----------

def parse_time_expression(text: str, now: datetime | None = None) -> datetime | None:
    """从一行里认 HH:MM 或 数字+单位 → 绝对到期时刻；认不出 / 不合规 → None（绝不出错）。

    - HH:MM：今天这个钟点；已经走了 → 明天同一钟点（她排的是"那个时刻"，不是"立刻"）
    - N+单位：从此刻起算 N 个 s/min/h 后
    """
    now = now or datetime.now()
    s = text.strip()
    if not s:
        return None

    m = _ABS_RE.match(s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if at <= now:                          # 那个钟点已经走了 → 等明天的同一钟点
            at += timedelta(days=1)
        return at

    m = _REL_RE.match(s)
    if m:
        n = float(m.group(1))
        unit = _UNITS[m.group(2)]
        return now + timedelta(**{unit: n})

    return None


# ---------- 存储 ----------

def read_store(path: Path | None = None) -> list[dict]:
    path = path or SCHEDULE_STORE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("items", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError, AttributeError):
        return []


def write_store(items: list[dict], path: Path | None = None) -> None:
    path = path or SCHEDULE_STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def pending(path: Path | None = None) -> list[dict]:
    """按到期先后排队的待开时刻（读侧，零写）。"""
    return sorted(read_store(path), key=lambda x: x.get("at", ""))


# ---------- 摄入 inbox ----------

def read_inbox(path: Path | None = None) -> str:
    path = path or SCHEDULE_IN
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def clear_inbox(path: Path | None = None) -> None:
    path = path or SCHEDULE_IN
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(INBOX_HEADER, encoding="utf-8")


def consume_inbox(cap: int = 24, inbox: Path | None = None,
                  store: Path | None = None,
                  now: datetime | None = None) -> list[dict]:
    """收 schedule_in.md 里的时刻进 store（上限 cap，超的只留最近 cap 条）。
    熟读即清：只把认出来的写进 store，inbox 清回 header。返回本次收进列表（空=没读到）。"""
    text = read_inbox(inbox)
    if not text.strip():
        return []
    now = now or datetime.now()
    items = read_store(store)
    seen = []
    for line in text.splitlines():
        at = parse_time_expression(line, now)
        if at is None:
            continue
        seen.append({"at": at.isoformat(timespec="seconds"),
                     "raw": line.strip()})
    if seen:
        items = (items + seen)[-cap:]
        write_store(items, store)
    clear_inbox(inbox)
    return seen


# ---------- 到点 ----------

def _is_due(item: dict, now: datetime) -> bool:
    try:
        return datetime.fromisoformat(item["at"]) <= now
    except (KeyError, TypeError, ValueError):
        return False


def peek_due(now: datetime | None = None, store: Path | None = None) -> dict | None:
    """最早到点那条；无 → None。只读，不开窗不烧。"""
    now = now or datetime.now()
    for it in pending(store):
        if _is_due(it, now):
            return it
    return None


def pop_due(now: datetime | None = None, store: Path | None = None) -> dict | None:
    """取走最早到点那条并落库（用完即焚）。只有开窗成功才该调它；
    精力不够没开成 → 留着，下个心跳再试（她说了到点，就一直等到真递到为止）。"""
    now = now or datetime.now()
    items = read_store(store)
    idx = next((i for i, it in enumerate(items) if _is_due(it, now)), None)
    if idx is None:
        return None
    item = items.pop(idx)
    write_store(items, store)
    return item
