"""
agent_admin.py — 读写 girl_workspace + 读取 OpenClaw 会话/记忆

后台与 OpenClaw 的唯一对话：
1. 把滑块渲染结果写回 girl_workspace/SOUL.md（会话起点读取 → 下条消息生效，无需重启）。
2. 读取 girl agent 的会话（sessions.json + sessionFile jsonl）做「记忆可视化」。
不直接发微信（单一出口由 OpenClaw / ClawBot 负责）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# OpenClaw 数据根（Windows 用户目录）
OPENCLAW_HOME = Path(os.path.expanduser("~")) / ".openclaw"

# girl agent 工作区
WORKSPACE = Path(__file__).resolve().parents[1] / "girl_workspace"

WORKSPACE_FILES = ["SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md"]

# girl agent 的会话目录
SESSIONS_DIR = OPENCLAW_HOME / "agents" / "girl" / "sessions"


# ============ 人格文件读写 ============

def read_file(name: str) -> str:
    """读 girl_workspace 里的一个文件（越界安全）。"""
    path = WORKSPACE / name
    if name not in WORKSPACE_FILES or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def apply_personality(slider_section: str) -> dict:
    """
    把渲染好的「滑块段」写进 SOUL.md，替换旧的滑块段。
    返回 {soul: 更新后的 SOUL.md, changed: 是否真变了}
    """
    from .soul_render import SLIDERS_MARKER

    soul_path = WORKSPACE / "SOUL.md"
    old = soul_path.read_text(encoding="utf-8") if soul_path.is_file() else ""

    changed = True
    mark_idx = old.find(SLIDERS_MARKER)
    if mark_idx != -1:
        # 保留滑块段之前的所有静态内容，替换到文件尾
        new_soul = old[:mark_idx] + slider_section
        changed = (new_soul != old)
    else:
        # 没有旧滑块段，直接追加
        new_soul = (old.rstrip() + "\n\n" + slider_section) if old.strip() else slider_section

    soul_path.write_text(new_soul, encoding="utf-8")
    return {"soul": new_soul, "changed": changed, "written": True}


# ============ 会话 / 记忆可视化 ============

def _safe_read_jsonl(path: Path, limit: int = 200):
    msgs = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or '"type":"message"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", {})
                role = msg.get("role")
                content = msg.get("content")
                text = _content_to_text(content)
                if role in ("user", "assistant") and text:
                    msgs.append({
                        "role": role,
                        "text": text,
                        "ts": obj.get("timestamp"),
                    })
                if len(msgs) >= limit:
                    break
    except OSError:
        return []
    return msgs


def _content_to_text(content) -> str:
    """把 message.content（字符串 或 分块数组）抽成纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("type")
                if t == "text" and block.get("text"):
                    parts.append(block["text"])
        return "".join(parts)
    return ""


def list_sessions() -> list[dict]:
    """列出 girl agent 的所有会话及其最近对话。"""
    if not SESSIONS_DIR.is_dir():
        return []
    sessions_map_path = SESSIONS_DIR / "sessions.json"
    sessions_map = {}
    if sessions_map_path.is_file():
        try:
            sessions_map = json.loads(sessions_map_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            sessions_map = {}

    # 汇总每个 origin 的会话元信息
    results = []
    for group_key, entries in sessions_map.items():
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sfile = entry.get("sessionFile")
            sfile_path = Path(sfile) if sfile else None
            messages = _safe_read_jsonl(sfile_path) if sfile_path else []
            results.append({
                "origin": entry.get("origin", {}).get("label", group_key),
                "sessionId": entry.get("sessionId"),
                "updatedAt": entry.get("updatedAt"),
                "messages": messages,
            })
    # 按更新时间倒序
    results.sort(key=lambda r: r.get("updatedAt") or 0, reverse=True)
    return results


def count_messages() -> int:
    """统计 girl 的所有消息条数（用于状态页）。"""
    total = 0
    for sess in list_sessions():
        total += len(sess.get("messages", []))
    return total
