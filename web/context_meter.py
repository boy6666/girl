"""context_meter.py — 每轮上下文开销计量 + 黄条判据（P0：只读数，不裁剪）。

数据双来源（都不碰 live 路径，读 OpenClaw 已写盘的日志）：
- trajectory（sessions/*.trajectory.jsonl）：`context.compiled` 事件带**完整拼装后的上下文**
  （systemPrompt 字符数 + messages 按角色字数 + tools 数）→ 量「系统恒量 vs 历史滚雪球」。
- 会话抄本（sessions/*.jsonl）：assistant 消息的 `usage` → 精确 input/output/cacheRead/cost。

增量解析：每文件记已读行数，新增行才追加进 data/context_stats_girl.jsonl；context_proxy
另写 data/context_stats_proxy.jsonl。两个事件文件 + 统一聚合 = /api/context/stats。

黄条判据（config.yaml 顶层 context_meter 段）：
- warn_turn_total_tokens   单轮总输入超阈
- warn_growth_days / _pct  对比窗口里每轮平均 tokens 涨幅超 %（历史滚雪球探针）
- warn_daily_cost_usd      单日开销超阈

P0 铁律：本模块只读 OpenClaw 日志 + 写自己的事件文件，绝不动 OpenClaw 配置/请求/文件。
裁剪（KEY_SEND_HISTORY_LIMIT 等价物）是 P1，不在本模块。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("context_meter")

# data/ 运行时目录默认相对仓库根
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSIONS_DIR = (
    Path.home() / ".openclaw" / "agents" / "girl" / "sessions"
)

METER_DEFAULTS = {
    "enabled": True,
    "mode": "meter",                 # meter | trim（trim 是 P1，现在只是哨位）
    "sessions_dir": "",              # 空 = ~/.openclaw/agents/girl/sessions
    "girl_log": "data/context_stats_girl.jsonl",
    "proxy_log": "data/context_stats_proxy.jsonl",
    "state_file": "data/context_meter_state.json",
    "warn_turn_total_tokens": 40000,
    "warn_growth_days": 3,        # 3 天就能看见雪球（08-20→08-22 每轮均值 52k→67k）
    "warn_growth_pct": 25,
    "warn_daily_cost_usd": 1.0,
    "upstreams": {},                 # 模型 → 上游（context_proxy 用）
    "proxy_port": 18781,
    "clean": {                       # 清洗器（P1 第一刀：心跳空轮折叠）
        "enabled": False,            # False=完全不参与
        "dry_run": True,             # True=只记账不改请求（铁律默认）
        "keep_recent_rounds": 1,     # 心跳轮最多保留最近几轮
    },
}


def load_meter_config(cfg_path: Path | None = None) -> dict:
    """读 data/config.yaml 顶层 context_meter 段并 merge 默认；缺文件/异常→纯默认。"""
    cfg = dict(METER_DEFAULTS)
    path = cfg_path or (REPO_ROOT / "data" / "config.yaml")
    raw = {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("context_meter") or {}
    except Exception:
        raw = {}
    for k, v in raw.items():
        if k in cfg:
            cfg[k] = v
    if not cfg["sessions_dir"]:
        cfg["sessions_dir"] = str(DEFAULT_SESSIONS_DIR)
    return cfg


def _resolve(cfg: dict, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else REPO_ROOT / p


# ============ 事件抽取（纯函数，便于单测） ============

def _trajectory_event(o: dict) -> dict | None:
    """context.compiled 行 → 系统/历史字符数事件。"""
    if o.get("type") != "context.compiled":
        return None
    d = o.get("data") or {}
    sys_text = d.get("systemPrompt") or ""
    history_chars = 0
    for m in d.get("messages") or []:
        c = m.get("content")
        if isinstance(c, str):
            history_chars += len(c)
        elif c:  # list of content blocks
            for blk in c:
                t = blk.get("text") if isinstance(blk, dict) else None
                if t:
                    history_chars += len(t)
    return {
        "type": "context.compiled",
        "ts": o.get("ts"),
        "provider": o.get("provider"),
        "model": o.get("modelId") or o.get("model"),
        "system_chars": len(sys_text),
        "history_chars": history_chars,
        "n_messages": len(d.get("messages") or []),
        "tools_n": len(d.get("tools") or []),
    }


def _find_usage(obj, depth: int = 0) -> dict | None:
    """会话抄本里松找 usage（message.usage 或深层嵌套），防结构漂移。"""
    if depth > 4 or not isinstance(obj, dict):
        return None
    if isinstance(obj.get("usage"), dict):
        u = obj["usage"]
        if "totalTokens" in u or ("input" in u and "output" in u):
            return u
    for v in obj.values():
        found = _find_usage(v, depth + 1)
        if found:
            return found
    return None


def _usage_event(o: dict, fname: str) -> dict | None:
    u = _find_usage(o)
    if not u:
        return None
    total = (u.get("totalTokens")) or 0
    if not (total or (u.get("input") or 0) or (u.get("output") or 0)):
        return None  # usage 占位/全零，非真实计费轮
    cost = u.get("cost") or {}
    msg = o.get("message") or {}   # 会话抄本把 provider/model/usage 放 message 里
    return {
        "type": "usage",
        "ts": o.get("timestamp") or o.get("ts"),
        "provider": msg.get("provider") or o.get("provider"),
        "model": msg.get("model") or o.get("modelId") or o.get("model"),
        "input": u.get("input") or 0,
        "output": u.get("output") or 0,
        "cacheRead": u.get("cacheRead") or 0,
        "cacheWrite": u.get("cacheWrite") or 0,
        "reasoning": u.get("reasoningTokens") or 0,
        "total": total,
        "cost": cost.get("total") if isinstance(cost, dict) else None,
        "src": fname,
    }


# ============ 增量解析 ============

def _iter_lines(path: Path, start: int):
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except json.JSONDecodeError:
                continue


def scan_and_append(cfg: dict) -> dict:
    """增量扫描 trajectory + 会话抄本 → 追加事件 → 返回本次扫描统计。"""
    girl_log = _resolve(cfg, cfg["girl_log"])
    state_path = _resolve(cfg, cfg["state_file"])
    sessions_dir = Path(cfg["sessions_dir"])
    state = {}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if \
            state_path.is_file() else {}
    except Exception:
        state = {}

    counts = {"trajectory": 0, "session": 0, "total_events": 0}
    appended: list[dict] = []
    if not girl_log.parent.exists():
        girl_log.parent.mkdir(parents=True, exist_ok=True)

    if sessions_dir.is_dir():
        for path in sorted(sessions_dir.glob("*.trajectory.jsonl")):
            key = f"traj:{path.name}"
            seen = state.get(key, {"lines": 0})
            new_lines = []
            last = seen["lines"]
            try:
                with path.open(encoding="utf-8") as f:
                    base = seen["lines"]
                    for i, line in enumerate(f):
                        last = i + 1
                        if i < base:
                            continue
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            o = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        ev = _trajectory_event(o)
                        if ev:
                            new_lines.append(ev)
                    state[key] = {"lines": last}
            except FileNotFoundError:
                continue
            for ev in new_lines:
                appended.append(ev)
                counts["trajectory"] += 1

        for path in sorted(sessions_dir.glob("*.jsonl")):
            key = f"ses:{path.name}"
            seen = state.get(key, {"lines": 0})
            new_evs = []
            last = seen["lines"]
            try:
                with path.open(encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        last = i + 1
                        if i < seen["lines"]:
                            continue
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            o = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        ev = _usage_event(o, path.name)
                        if ev:
                            new_evs.append(ev)
                    state[key] = {"lines": last}
            except FileNotFoundError:
                continue
            for ev in new_evs:
                appended.append(ev)
                counts["session"] += 1

    if appended:
        with girl_log.open("a", encoding="utf-8") as f:
            for ev in appended:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    try:
        state_path.write_text(
            json.dumps(state, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        log.warning("写状态失败: %s", e)
    counts["total_events"] = len(appended)
    return counts


# ============ 聚合 + 黄条判据 ============

def _parse_ts(ev: dict) -> datetime | None:
    ts = ev.get("ts")
    if not ts:
        return None
    if isinstance(ts, (int, float)):
        # 可能是毫秒/秒纪元
        return datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts)
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_events(cfg: dict) -> list[dict]:
    evs: list[dict] = []
    for rel in (cfg["girl_log"], cfg["proxy_log"]):
        p = _resolve(cfg, rel)
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    evs.sort(key=lambda e: e.get("ts") or "")
    return evs


def _usage_only(evs: list[dict]) -> list[dict]:
    return [e for e in evs if e.get("type") == "usage"]


def build_stats(cfg: dict | None = None) -> dict:
    """全量：增量扫盘 → 聚合 → 黄条判据。供 /api/context/stats 调用。"""
    cfg = cfg or load_meter_config()
    scan = scan_and_append(cfg)
    evs = _load_events(cfg)
    usage = _usage_only(evs)
    compiled = [e for e in evs if e.get("type") == "context.compiled"]

    # 按日聚合（本地日期，粗暴从 ts 取日期段）
    daily: dict[str, dict] = {}
    for e in usage:
        dt = _parse_ts(e)
        day = dt.strftime("%Y-%m-%d") if dt else "?"
        d = daily.setdefault(day, {
            "turns": 0, "input": 0, "output": 0, "cacheRead": 0,
            "total": 0, "cost": 0.0,
        })
        d["turns"] += 1
        d["input"] += e.get("input") or 0
        d["output"] += e.get("output") or 0
        d["cacheRead"] += e.get("cacheRead") or 0
        d["total"] += e.get("total") or 0
        d["cost"] += e.get("cost") or 0.0
    for d in daily.values():
        d["avg_turn"] = round(d["total"] / d["turns"], 0) if d["turns"] else 0

    # 最近 N 轮（usage 为主；compiled 合并展示）
    latest_usage = [dict(e) for e in usage[-12:][::-1]]
    for e in latest_usage:
        e["_kind"] = "usage"
    latest_compiled = [dict(e) for e in compiled[-3:][::-1]]
    for e in latest_compiled:
        e["_kind"] = "compiled"

    # —— 黄条判据 ——
    warns: list[dict] = []
    today = datetime.now().strftime("%Y-%m-%d")
    if usage:
        last = usage[-1]
        if (last.get("total") or 0) > cfg["warn_turn_total_tokens"]:
            warns.append({
                "level": "warn",
                "msg": f"单轮输入 {last.get('total')} tokens 超阈值 "
                       f"{cfg['warn_turn_total_tokens']}",
                "data": last,
            })

    days = sorted(daily.keys())
    if len(days) >= 2:
        # 当日(或最近一天)开销
        ref_day = days[-1]
        if ref_day == today and len(days) >= 2:
            ref_day = days[-2]
        cost = daily[ref_day]["cost"]
        if cost > cfg["warn_daily_cost_usd"]:
            warns.append({
                "level": "warn",
                "msg": f"{ref_day} 开销 ${cost:.3f} 超阈值 "
                       f"${cfg['warn_daily_cost_usd']}",
                "data": {"day": ref_day, "cost": cost},
            })

    # 滚雪球：最近 W 天 vs 之前 W 天的每轮均值涨幅
    w = max(1, int(cfg["warn_growth_days"]))
    if len(days) >= 2 * w:
        recent = days[-w:]
        prior = days[-2 * w:-w]
        def avg(day_list):
            tot = totn = 0
            for dd in day_list:
                tot += daily[dd]["total"]
                totn += daily[dd]["avg_turn"] or 0
            n = max(1, sum(daily[dd]["turns"] for dd in day_list))
            return tot / n
        r, p = avg(recent), avg(prior)
        if p > 0:
            pct = round((r - p) / p * 100, 1)
            if pct > cfg["warn_growth_pct"]:
                warns.append({
                    "level": "warn",
                    "msg": f"近 {w} 天每轮均值 {r:.0f} 比前 {w} 天 {p:.0f} "
                           f"涨 {pct}%（历史滚雪球探针，超 {cfg['warn_growth_pct']}%）",
                    "data": {"recent": r, "prior": p, "pct": pct},
                })

    latest_compiled_summary = compiled[-1] if compiled else {}
    return {
        "ok": True,
        "mode": cfg.get("mode", "meter"),
        "enabled": bool(cfg.get("enabled", True)),
        "scan": scan,
        "totals": {
            "usage_events": len(usage),
            "compiled_events": len(compiled),
        },
        "latest_compiled": latest_compiled_summary,
        "latest_turns": latest_usage,
        "daily": [{"day": d, **daily[d]} for d in days[-14:]],
        "warns": warns,
        "thresholds": {
            "turn_total_tokens": cfg["warn_turn_total_tokens"],
            "growth_days": cfg["warn_growth_days"],
            "growth_pct": cfg["warn_growth_pct"],
            "daily_cost_usd": cfg["warn_daily_cost_usd"],
        },
    }
