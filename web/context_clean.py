"""context_clean.py — 上下文清洗器（P1 第一刀：心跳空轮折叠）。

对齐爱语「上下文清洗」（业务串清单:156-162：把 AI 自己的循环过程噪音从下一轮
请求上下文里摘除）落到本地，清洗对象是**发往上游的 messages**（网关这一层能控的
只有这个）。

以真实 compiled 证据定位可清噪音（2026-08-23 实测）：
OpenClaw 每 30 分钟一轮 heartbeat 空轮——
    user=[OpenClaw heartbeat poll]
    → assistant(空 thinking) → toolResult(读一遍空 heartbeat.md) → assistant("空的")
这类轮次：0 对话价值、纯重复，sessions 尾部 65 条里占了 40 条，是历史滚雪球的
主力。折叠策略：把连续心跳轮只留最近 keep_recent_rounds 轮（默认 1），前面的整段
删掉，保留最近一条让模型知道"刚查过是空的"，防立刻重复主动。

P0 铁律演进：本模块是**纯函数**，永远返回 (新列表, 统计)，从不自己决定改不改；
由调用方（context_proxy）按 config.clean 决定 dry_run（只记账）还是真应用。
默认 dry_run——不套真实流量前绝不改任何请求。
"""
from __future__ import annotations

# 心跳轮 user 消息的特征标记（OpenClaw 主动 poll 用；覆盖可能的大小写变体）
HEARTBEAT_MARKERS = ("heartbeat poll", "heartbeat", "HEARTBEAT")

DEFAULTS = {
    "enabled": False,        # 总开关：False = 完全不参与
    "dry_run": True,         # True = 只算 would_clean 账，不改 body（铁律默认）
    "keep_recent_rounds": 1,  # 心跳轮最多保留最近几轮
}

# ---- 纯函数：检测 + 切轮 + 折叠 ----


def _is_heartbeat_round(r: list) -> bool:
    """一轮里 user 消息是否长得像心跳 poll（OpenClaw heartbeat 特征文本）。"""
    for m in r:
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str) and any(k in c for k in HEARTBEAT_MARKERS):
            return True
        if isinstance(c, list):
            for b in c:
                t = (b.get("text") or "") if isinstance(b, dict) else ""
                if any(k in t for k in HEARTBEAT_MARKERS):
                    return True
    return False


def _round_chars(r: list) -> int:
    n = 0
    for m in r:
        c = m.get("content")
        if isinstance(c, str):
            n += len(c)
        elif isinstance(c, list):
            n += sum(len(b.get("text") or "") for b in c if isinstance(b, dict))
    return n


def split_rounds(messages: list) -> list:
    """按 user 起头切成一轮一轮（每条 user 代表一轮开始，跨 role 保持完整）。"""
    rounds: list[list] = []
    cur: list = []
    for m in messages:
        if cur and m.get("role") == "user":
            rounds.append(cur)
            cur = []
        cur.append(m)
    if cur:
        rounds.append(cur)
    return rounds


def clean_messages(messages: list, keep_recent_rounds: int = 1) -> tuple:
    """折叠连续心跳空轮 → (新列表, 统计)。

    纯函数：不修改入参；不做任何决定，由调用方决定用不用新列表。
    统计字段与 proxy 观察事件同构：merged_rounds / removed_chars / kept_heartbeat。
    """
    if not messages:
        return list(messages), {"merged_rounds": 0, "removed_chars": 0,
                                "kept_heartbeat": 0, "n_before": 0, "n_after": 0}
    rounds = split_rounds(messages)
    keep = max(1, int(keep_recent_rounds))

    kept: list[list] = []
    merged = 0
    removed_chars = 0
    hb_kept = 0

    i = 0
    n = len(rounds)
    while i < n:
        if _is_heartbeat_round(rounds[i]):
            # 找连续心跳段
            j = i
            while j < n and _is_heartbeat_round(rounds[j]):
                j += 1
            seg = rounds[i:j]
            if len(seg) > keep:
                # 折叠：删前 len-keep 轮，留最后 keep 轮
                for r in seg[:-keep]:
                    merged += 1
                    removed_chars += _round_chars(r)
                kept.extend(seg[-keep:])
                hb_kept += keep
            else:
                kept.extend(seg)
                hb_kept += len(seg)
            i = j
        else:
            kept.append(rounds[i])
            i += 1

    flat: list = []
    for r in kept:
        flat.extend(r)
    return flat, {
        "merged_rounds": merged,
        "removed_chars": removed_chars,
        "kept_heartbeat": hb_kept,
        "n_before": len(messages),
        "n_after": len(flat),
    }


def build_clean_stats(messages: list) -> dict:
    """供 proxy 观察事件用：不管 enabled/dry_run，先算出'如果清会怎么着'。"""
    _, st = clean_messages(messages)
    return st
