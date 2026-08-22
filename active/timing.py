"""timing.py — 从 OpenClaw 自带的会话轨迹合成"每环节耗时"。

OpenClaw 每次 run 都会写一个 `<sessionId>.trajectory.jsonl`，每行一个环节事件，
顶层带 ISO 时间戳 `ts`：session.started → context.compiled → prompt.submitted →
model.completed → session.ended。有工具调用时 prompt.submitted/model.completed 会
成对出现多次（每次 = 一次 LLM 往返，中间夹一次工具执行）。

我们不另埋钟，只做解析/聚合——纯函数，合成文本即可测。
用途：看清"回消息慢"到底慢在哪一段（几乎总是模型生成）。
"""
from __future__ import annotations

import glob
import json
import statistics
from datetime import datetime
from pathlib import Path


def _parse_ts(t) -> datetime | None:
    if not t:
        return None
    try:
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def parse_trajectory(text: str) -> list[dict]:
    """把一份 trajectory 文本解析成有序事件 [{type, ts: datetime|None}]。

    坏行/无 type 的行跳过。★ 绝不因一行坏数据让整份计时崩掉。
    """
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict) or o.get("type") is None:
            continue
        out.append({"type": o["type"], "ts": _parse_ts(o.get("ts"))})
    return out


# 相邻环节对 → 人类可读的环节名（其余对按 type 拼）
_SEG_LABEL = {
    ("session.started", "context.compiled"): "提示词构建",
    ("context.compiled", "prompt.submitted"): "注入收尾",
    ("prompt.submitted", "model.completed"): "LLM 生成",
    ("model.completed", "prompt.submitted"): "工具执行(往返)",
    ("model.completed", "session.ended"): "收尾",
}
_LLM_PAIR = ("prompt.submitted", "model.completed")


def stage_breakdown(events: list[dict]) -> dict:
    """把有序事件压成环节耗时。

    返回 {
      total: 整轮耗时（首末事件差，秒）,
      llm:   {count: 几次 LLM 生成, seconds: 生成总耗时},
      segments: [{name, seconds}] 相邻环节的耗时分段（只剪识别出的环节对）。
    }
    ts 缺失时向前继承（不因个别缺 ts 丢整段）。
    """
    last_ts = None
    ts_seq = []
    for e in events:
        if e["ts"] is not None:
            last_ts = e["ts"]
        ts_seq.append(e["ts"] if e["ts"] is not None else last_ts)

    segments = []
    llm_count = 0
    llm_sec = 0.0
    for i in range(1, len(events)):
        a, b = ts_seq[i - 1], ts_seq[i]
        if a is None or b is None:
            continue
        dt = (b - a).total_seconds()
        ta, tb = events[i - 1]["type"], events[i]["type"]
        name = _SEG_LABEL.get((ta, tb), f"{ta}→{tb}")
        if (ta, tb) == _LLM_PAIR:
            llm_count += 1
            llm_sec += dt
        segments.append({"name": name, "seconds": round(dt, 3)})

    total = None
    if ts_seq and ts_seq[0] is not None and ts_seq[-1] is not None:
        total = round((ts_seq[-1] - ts_seq[0]).total_seconds(), 3)

    return {"total": total,
            "llm": {"count": llm_count, "seconds": round(llm_sec, 3)},
            "segments": segments}


def summarize_sessions(sessions_dir, limit: int = 10) -> dict:
    """扫一个会话目录里的 *.trajectory.jsonl，按修改时间取最近 limit 份，
    各自出分段耗时，并聚合 LLM/整轮的平均/最大/最小。坏文件自动跳过。"""
    paths = sorted(glob.glob(str(Path(sessions_dir) / "*.trajectory.jsonl")),
                   key=lambda p: Path(p).stat().st_mtime, reverse=True)[:limit]
    runs = []
    for p in paths:
        try:
            text = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        evs = parse_trajectory(text)
        if not evs:
            continue
        b = stage_breakdown(evs)
        runs.append({"file": Path(p).name,
                     "total": b["total"],
                     "llm_seconds": b["llm"]["seconds"],
                     "llm_count": b["llm"]["count"],
                     "segments": b["segments"]})

    def _agg(key):
        vals = [r[key] for r in runs if r[key] is not None]
        if not vals:
            return None
        return {"avg": round(statistics.mean(vals), 3),
                "max": round(max(vals), 3),
                "min": round(min(vals), 3)}

    return {"runs": runs,
            "aggregate": {
                "count": len(runs),
                "llm_seconds": _agg("llm_seconds"),
                "total": _agg("total"),
            }}


def main() -> None:
    """CLI：python -m active.timing [sessions_dir]。终端打印每轮分段 + 聚合。"""
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    default = str(Path.home() / ".openclaw" / "agents" / "girl" / "sessions")
    target = sys.argv[1] if len(sys.argv) > 1 else default
    s = summarize_sessions(target)
    ag = s["aggregate"]
    print("会话目录:", target, "  最近 %d 轮\n" % ag["count"])
    for r in s["runs"]:
        seg = "  ".join("%s=%.2fs" % (x["name"], x["seconds"]) for x in r["segments"])
        print("%-52s 整轮=%ss" % (r["file"], r["total"]))
        print("    " + seg)
    print("\n聚合(最近 %d 轮):" % ag["count"])
    print("  LLM 生成  %s" % _fmt(ag["llm_seconds"]))
    print("  整轮      %s" % _fmt(ag["total"]))
    print("\n→ 哪一段最贵,一眼可见。LLM 生成(模型耗时)通常占 99%+,其余毫秒级。")


def _fmt(a) -> str:
    if a is None:
        return "无数据"
    return "平均 %.2fs / 最快 %.2fs / 最慢 %.2fs" % (a["avg"], a["min"], a["max"])


if __name__ == "__main__":
    main()
