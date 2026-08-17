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


# ===== 反思（V3 自我反思）参数 =====
REFLECTION_DEFAULTS = {
    "enabled": True,             # 是否每晚反思
    "window": "22:00",           # 每晚窗口 HH:MM（24h），避开主动开窗
    "provider": "dry_run",       # dry_run | openclaw（openclaw 才写 reflect.md）
}


def merge_reflection_config(raw: dict | None = None) -> dict:
    cfg = dict(REFLECTION_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_reflection_config(cfg_path: Path | None = None) -> dict:
    """读 data/config.yaml 的顶层 reflection 段并 merge 默认。"""
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("reflection") or {}
    except Exception:
        raw = {}
    return merge_reflection_config(raw)


# ===== 作息（circadian）—— 她有自己的生活节奏，可由当天忙碌/相处双向漂移 =====
CIRCADIAN_DEFAULTS = {
    "bedtime": "23:00",          # 基础就寝 HH:MM
    "wake": "08:00",             # 基础起床 HH:MM
    "early_bedtime": "21:00",    # 内驱/早睡时的就寝下限（最早就寝）
    "late_band_end": "03:00",    # 晚睡深夜带上界（从他聊到就寝后算起，跨午夜）
    "max_shift_min": 240,        # 最多同时后延/前移（分钟，4h）
    "own_load_min_per_item": 20, # 她今天每件真实事压早就寝的分钟数
}


def merge_circadian_config(raw: dict | None = None) -> dict:
    cfg = dict(CIRCADIAN_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_circadian_config(cfg_path: Path | None = None) -> dict:
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("circadian") or {}
    except Exception:
        raw = {}
    return merge_circadian_config(raw)


# ===== 日记（每晚·她第一人称叙事） =====
DIARY_DEFAULTS = {
    "enabled": True,             # 是否每晚写日记
    "provider": "dry_run",       # dry_run | openclaw（openclaw 才写 diary_in.md）
}


def merge_diary_config(raw: dict | None = None) -> dict:
    cfg = dict(DIARY_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_diary_config(cfg_path: Path | None = None) -> dict:
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("diary") or {}
    except Exception:
        raw = {}
    return merge_diary_config(raw)


# ===== 持续生长（低频率·在 GROWTH.md 底子上续长） =====
GROWTH_DEFAULTS = {
    "enabled": True,             # 是否周期性问她"后来你又长成什么样"
    "interval_days": 3,         # 几天才问一次（生长是慢的）
    "provider": "dry_run",       # dry_run | openclaw（openclaw 才写 growth_in.md）
}


def merge_growth_config(raw: dict | None = None) -> dict:
    cfg = dict(GROWTH_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_growth_config(cfg_path: Path | None = None) -> dict:
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("growth") or {}
    except Exception:
        raw = {}
    return merge_growth_config(raw)


# ===== 梦（非每日·真实日间残余做由头） =====
DREAM_DEFAULTS = {
    "enabled": True,             # 是否做非每日的梦
    "provider": "dry_run",       # dry_run | openclaw（openclaw 才写 dream_in.md）
}


def merge_dream_config(raw: dict | None = None) -> dict:
    cfg = dict(DREAM_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def load_dream_config(cfg_path: Path | None = None) -> dict:
    path = cfg_path or (Path(__file__).resolve().parents[1] / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("dream") or {}
    except Exception:
        raw = {}
    return merge_dream_config(raw)
