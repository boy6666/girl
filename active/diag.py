"""diag.py — "主动发送链路"诊断：为什么她没自动发消息。

把整条链路拆成可见的环节，逐个报告状态，方便一眼看到断在哪：
  A. Python 心跳是否在推进状态（线程活着？provider 接真没有？）
  B. 状态机的"窗口"守卫逐条：值 / 阈值 / 放行与否 —— window_gates
  C. 动机卡片有没有真的写进 girl 的摄入文件（OpenClaw 心跳能不能读到）

只读，无副作用。供 GET /api/active/diag 使用；纯函数，可测。
"""
from datetime import datetime
from pathlib import Path

from . import state_store, state_machine, injector

# 摄入文件里以 <!-- 开头的行算注释（空/纯注释 = 无事可说）
_COMMENT_PREFIX = ("<!--", "#")


def _non_comment_tail(path: Path, n: int = 5) -> list:
    """返回文件里非注释的最近 n 行（卡片内容片段），空列表=没有卡在等。"""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [ln for ln in lines
            if ln.strip() and not ln.lstrip().startswith(_COMMENT_PREFIX)][-n:]


def heartbeat_link(state: dict, config: dict, heartbeat_path: Path,
                now=None) -> dict:
    """C 环节：卡片有没有进摄入文件。"""
    now = now or datetime.now()
    pending = _non_comment_tail(heartbeat_path)
    mtime = None
    if heartbeat_path.exists():
        try:
            mtime = datetime.fromtimestamp(heartbeat_path.stat().st_mtime)
        except OSError:
            pass
    return {
        "path": str(heartbeat_path),
        "exists": heartbeat_path.exists(),
        "has_pending_card": bool(pending),
        "pending_snippet": pending,
        "last_written": mtime.isoformat(timespec="seconds") if mtime else None,
        "age_minutes": round((now - mtime).total_seconds() / 60, 1) if mtime else None,
        "note": (
            "文件里有卡片在等 OpenClaw 心跳消费（会由小语决定发不发）"
            if pending else
            "文件为空/只有注释 = 没有新的动机卡片。既可能是 Python 心跳没写进，"
            "也可能是 OpenClaw 已消费并发过/决定静默"),
    }


def proactive_diag(cfg_path: Path, state_path: Path,
                  heartbeat_path: Path | None = None, now=None) -> dict:
    """聚合 A/B/C 三环节的链路诊断。A 的线程存活由调用方（web 层）补填。"""
    import yaml
    from . import config as cfgmod

    now = now or datetime.now()
    raw = {}
    try:
        if cfg_path.is_file():
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:                                        # noqa: BLE001
        pass
    config = cfgmod.merge_config(raw.get("active_behavior", {}))
    state = state_store.load(state_path)
    if not state.get("initialized"):
        state = state_store.default_state()

    hb = heartbeat_path or injector.HEARTBEAT_PATH
    gates = state_machine.window_gates(state, config, now)
    window_open = all(g["ok"] for g in gates)
    blocked = [g for g in gates if not g["ok"]]

    return {
        "now": now.isoformat(timespec="seconds"),
        "state_machine": {
            "energy": round(state.get("energy", 0), 1),
            "mood": round(state.get("mood", 0), 3),
            "social_need": round(state.get("social_need", 0), 3),
            "today_active_count": state.get("today_active_count", 0),
            "unanswered_count": state.get("unanswered_count", 0),
            "awaiting_reply": state.get("awaiting_reply", False),
            "last_real_reply": state.get("last_real_reply"),
            "last_active_ts": state.get("last_active_ts"),
        },
        "inject_provider": config.get("inject_provider", "dry_run"),
        "tick_minutes": config.get("tick_minutes", 15),
        "window_open": window_open,
        "window": {
            "open": window_open,
            "gates": gates,
            "blocked": blocked,
            "verdict": (
                "窗口开着 → 心跳会把动机卡片写给 Girl" if window_open
                else "窗口关着。卡在："
                     + "、".join(g["gate"] for g in blocked)),
        },
        "heartbeat_link": heartbeat_link(state, config, hb, now),
        "who_sends": (
            "OpenClaw（微信统一出口）。Python 只写卡片，由小语决定说不说、发不发。"
            if config.get("inject_provider", "dry_run") == "openclaw"
            else "dry_run：Python 只算卡片不写文件 —— 这本身就是「没在发」的原因之一。"),
    }
