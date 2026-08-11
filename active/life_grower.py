"""life_grower.py — 生成当天生活日志条目。
provider="dry_run": 用内容库种子拼接（零依赖、可测、确定性）。
provider="openclaw": 交给 girl agent 用真实声音写当天生活（Task 14 接 injector）。
"""
import random


def _pick(bucket: list[str], day: str, rng) -> str:
    return rng.choice(bucket or ["随意过了大半天"])


def _seed_entry(content: dict, journal_text: str, day: str, seed=None) -> str:
    """dry_run 兜底：只拼用户填过的真实事实；没有就不硬造（平淡留白）。"""
    rng = random.Random(seed if seed is not None else day)
    buckets = content.get("buckets", {})
    parts = []
    for b in ("morning", "work", "afternoon", "evening"):
        pool = buckets.get(b, [])
        if pool:
            parts.append(rng.choice(pool))
    if not parts:
        return "今天平平淡淡，没什么特别的事。"
    return "。".join(parts) + "。"


def grow_today(content: dict, journal_text: str, day: str,
               provider: str = "dry_run", seed=None) -> str:
    if provider == "openclaw":
        # Task 14 接入：经 injector 唤醒 girl agent 以第一人称写今天生活（内部，不发）
        from .injector import generate_text
        return generate_text(
            "你是小语。请用你自己的口吻，写一小段(3-5句)今天你经历了什么、想到什么。"
            "这是内部的生活日记，不是发给主人的消息，不用称呼主人、不用问候、不用结尾问句。"
            f"\n今天日期:{day}\n你的生活底色:{content}\n之前的生活日志:\n{journal_text or '(还没有)'}",
            provider=provider)
    return _seed_entry(content, journal_text, day, seed)
