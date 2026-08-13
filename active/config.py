"""config.py — 主动状态机全部参数（唯一真相，落点 data/config.yaml 的 active_behavior 段）。"""
from pathlib import Path

CONFIG_DEFAULTS = {
    "open_threshold": 0.5,           # 社交需求达到多少才考虑开窗
    "cooldown_seconds": 300,         # 主动冷却（秒）
    "daily_max": 2,                  # 每日主动上限（次）
    "quiet_start": 2,                # 勿扰硬墙开始（时）——绝不在这些时辰主动
    "quiet_end": 5,                  # 勿扰硬墙结束（时）
    "max_unanswered": 3,             # 连续未回上限（达到暂停催人）
    "allow_late_night": True,        # 是否允许凌晨/深夜软窗口
    "late_night_start": 23,          # 深夜软窗口开始（时）
    "early_morning_end": 6,          # 深夜软窗口结束（时）
    "tick_minutes": 15,              # 心跳间隔（分钟）
    "growth_rate_per_hour": 0.12,    # 思念涨速（每小时基数）
    "energy_time_constant_min": 240, # 精力漂移常数（4h）
    "mood_time_constant_min": 360,   # 情绪回基线常数（6h）
    "mood_baseline": 0.15,           # 情绪基线
    "attachment": "secure",          # secure | anxious | avoidant
    "seed_energy": 80.0,
    "seed_mood": 0.2,
    "grow_provider": "dry_run",      # dry_run | openclaw（真生长见 Task 14）
    "inject_provider": "dry_run",    # dry_run | openclaw（真注入见 Task 14）
    "emoji_mode": "off",                    # off | char | image — 表情出口；image 需接真后再启用
    "emoji_sources": ["adesk", "sogou"],    # image 模式的稳定图源，可自配
    "emoji_media_dir": "data/media",        # 本地表情包文件夹（相对仓库根，gitignored）
    "emoji_media_ttl_days": 14,             # 旧图自动清理（天）
}


def merge_config(raw: dict | None = None) -> dict:
    cfg = dict(CONFIG_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_config(cfg_path: Path | None = None) -> dict:
    """读 data/config.yaml 的 active_behavior 段并 merge 默认；缺文件/异常→纯默认。"""
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("active_behavior") or {}
    except Exception:
        raw = {}
    return merge_config(raw)
