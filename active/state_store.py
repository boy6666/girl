"""state_store.py — data/state.json 读写（runtime 主动状态，gitignore）。"""
import json
from datetime import datetime
from pathlib import Path

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "state.json"


def default_state(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    return {
        "initialized": False,        # 首次 tick 由 config.seed_energy/seed_mood 填入
        "energy": None,              # 0~100
        "mood": None,                # -1~+1
        "social_need": 0.0,          # 0~1
        "last_real_reply": None,     # iso 时间戳
        "last_active_ts": None,
        "unanswered_count": 0,
        "today_active_count": 0,
        "last_reflection_date": None,    # 上次反思日期 YYYY-MM-DD（防每晚重复）
        "last_diary_date": None,         # 上次写日记日期（防每晚重复）
        "last_dream_date": None,         # 上次写梦记日期（防重复）
        "last_growth_date": None,         # 上次"持续生长"提问日（低频，防每天催长）
        "today": now.strftime("%Y-%m-%d"),
        "awaiting_reply": False,
    }


def load(path: Path = DEFAULT_STATE_PATH) -> dict:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    base = default_state()
    base.update({k: v for k, v in data.items() if k in base})
    return base


def save(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
