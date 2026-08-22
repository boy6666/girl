"""timing 链路计时：从 OpenClaw 的 trajectory.jsonl 合成"每环节耗时"。

数据来源是 OpenClaw 自带的会话轨迹（每个轨迹行带 ts），不是我们埋的钟——
读者只做解析/聚合，纯函数，用合成文本驱动（不依赖线上文件）。
"""
import pytest

from active.timing import (parse_trajectory, stage_breakdown,
                           summarize_sessions)

# ---- 一段 heartbeat 风格轨迹：单次 LLM 调用，无工具往返 ----
HEARTBEAT = (
    '{"type":"session.started","ts":"2026-08-20T08:34:35.756Z"}\n'
    '{"type":"context.compiled","ts":"2026-08-20T08:34:35.787Z"}\n'
    '{"type":"prompt.submitted","ts":"2026-08-20T08:34:35.798Z"}\n'
    '{"type":"model.completed","ts":"2026-08-20T08:34:46.741Z"}\n'
    '{"type":"session.ended","ts":"2026-08-20T08:34:46.743Z"}\n'
)

# ---- 带工具往返：两次 LLM 调用（中间夹一次工具执行）+ 一次递送 ----
WITH_TOOL = (
    '{"type":"session.started","ts":"2026-08-20T09:00:00.000Z"}\n'
    '{"type":"context.compiled","ts":"2026-08-20T09:00:00.040Z"}\n'
    '{"type":"prompt.submitted","ts":"2026-08-20T09:00:00.050Z"}\n'
    '{"type":"model.completed","ts":"2026-08-20T09:00:04.050Z"}\n'   # LLM #1: 4.0s
    '{"type":"prompt.submitted","ts":"2026-08-20T09:00:04.350Z"}\n'   # tool#1: 0.3s
    '{"type":"model.completed","ts":"2026-08-20T09:00:07.850Z"}\n'   # LLM #2: 3.5s
    '{"type":"session.ended","ts":"2026-08-20T09:00:07.900Z"}\n'
)


def test_parse_trajectory_builds_ordered_events():
    evs = parse_trajectory(HEARTBEAT)
    assert [e["type"] for e in evs] == [
        "session.started", "context.compiled", "prompt.submitted",
        "model.completed", "session.ended"]
    assert evs[0]["ts"] is not None
    assert evs[0]["ts"].isoformat() == "2026-08-20T08:34:35.756000+00:00"


def test_parse_skips_non_json_lines():
    txt = HEARTBEAT + 'not-json-line\n'
    assert len(parse_trajectory(txt)) == 5


def test_heartbeat_breakdown_names_the_dominant_stage():
    b = stage_breakdown(parse_trajectory(HEARTBEAT))
    assert b["llm"]["count"] == 1
    assert b["llm"]["seconds"] == pytest.approx(10.943, abs=0.001)
    # LLM 生成是大头：比提示词构建 (0.03s) 大三四个量级
    assert b["llm"]["seconds"] > 100 * b["segments"][0]["seconds"]
    assert b["total"] == pytest.approx(10.987, abs=0.001)


def test_tool_loop_breaks_into_two_llm_plus_tool():
    b = stage_breakdown(parse_trajectory(WITH_TOOL))
    assert b["llm"]["count"] == 2
    assert b["llm"]["seconds"] == pytest.approx(7.5, abs=0.001)
    # 名字里要能看出"工具执行(往返)"
    names = [s["name"] for s in b["segments"]]
    assert any("工具" in n for n in names)
    assert b["total"] == pytest.approx(7.9, abs=0.001)


def test_summarize_sessions_aggregates_llm(tmp_path):
    (tmp_path / "a.trajectory.jsonl").write_text(HEARTBEAT, encoding="utf-8")   # llm 10.943
    (tmp_path / "b.trajectory.jsonl").write_text(WITH_TOOL, encoding="utf-8")   # llm 7.5
    # 杂物文件不该被当轨迹
    (tmp_path / "c.jsonl").write_text("not-a-trajectory", encoding="utf-8")
    s = summarize_sessions(tmp_path)
    assert len(s["runs"]) == 2
    agg = s["aggregate"]
    assert agg["count"] == 2
    assert agg["llm_seconds"]["avg"] == pytest.approx((10.943 + 7.5) / 2, abs=0.001)
    assert agg["llm_seconds"]["max"] == pytest.approx(10.943, abs=0.001)
    assert agg["llm_seconds"]["min"] == pytest.approx(7.5, abs=0.001)
    # 每个 run 都要能翻出分段，方便看"哪一段最贵"
    assert all(r["segments"] for r in s["runs"])


def test_summarize_sessions_empty_dir(tmp_path):
    assert summarize_sessions(tmp_path)["aggregate"]["count"] == 0
