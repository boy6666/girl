"""injector.py — 把动机卡片交给谁去说。单一出口约束：
Python 永不直接发微信。这里只负责给 girl agent（OpenClaw）送"动机卡片"，
由 agent 用自己的声音决定说不说、说什么，再由 OpenClaw 发出去。
默认 provider="dry_run"：只打印不发送，保证后端无副作用、可测。
（真 OpenClaw 注入在 Task 14 接线，签名不变。）
"""
import logging

log = logging.getLogger("active.injector")


def generate_text(prompt: str, provider: str = "dry_run") -> str:
    """给 life_grower：让模型/agent 生成自由文本（这里只回空，真实现见 Task 14）。"""
    log.info("generate_text(%s) dry-run prompt=%s", provider, prompt[:50])
    return ""


def inject_motivation(card: str, provider: str = "dry_run") -> dict:
    if provider == "openclaw":
        # Task 14 接真实注入：静默唤醒 girl agent，把 card 注入其 heartbeat，
        # 由 agent 决定说不说。此处暂不实现发送。
        log.info("inject openclaw card=%s", card[:80])
        return {"provider": "openclaw", "sent": False, "card": card,
                "note": "真实注入在 Task 14 实现"}
    log.debug("dry-run card=%s", card)
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}
