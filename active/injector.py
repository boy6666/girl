"""injector.py — 把动机卡片交给谁去说。单一出口约束：
Python 永不直接发微信。这里只负责把"动机卡片"写进 girl agent（OpenClaw）的
心跳摄入文件，由 agent 用自己的声音决定说不说、说什么，再由 OpenClaw 发出去。
默认 provider="dry_run"：只打印不写文件、不发送，保证后端无副作用、可测。
provider="openclaw"：把 card 追加到心跳文件（已接通的 OpenClaw 心跳链路消费它）。
"""
import logging
from pathlib import Path

log = logging.getLogger("active.injector")

# girl agent 心跳摄入文件（gitignored，见 .gitignore girl_workspace/memory/）
HEARTBEAT_PATH = Path(__file__).resolve().parents[1] / "girl_workspace" / "memory" / "heartbeat.md"


def generate_text(prompt: str, provider: str = "dry_run") -> str:
    """给 life_grower：让模型/agent 生成自由文本。
    provider="openclaw"：真实生成由已接通的 OpenClaw 侧完成，这里只记录请求，
    不直接调用模型（Python 不碰模型/网关）。"""
    log.info("generate_text(%s) prompt=%s", provider, prompt[:80])
    if provider == "openclaw":
        return ""   # 真生长由 OpenClaw 链路产出；接口保持返回 str
    return ""


def inject_motivation(card: str, provider: str = "dry_run",
                      heartbeat_path: Path | None = None) -> dict:
    if provider == "openclaw":
        path = heartbeat_path or HEARTBEAT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(card.rstrip() + "\n")
        log.info("inject openclaw card written to %s", path)
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(path), "card": card,
                "note": "已写入心跳文件，由 OpenClaw 链路消费并决定是否真发"}
    log.debug("dry-run card=%s", card)
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}
