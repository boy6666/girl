"""diag 链路诊断：window_gates 逐条给出值/阈值/放行，摄入文件能读出"有卡在等"。"""
from datetime import datetime

from active import config as cfgmod, state_machine
from active.diag import _non_comment_tail
import pytest


def _base(**kw):
    s = {
        "initialized": True, "energy": 80.0, "mood": 0.2,
        "social_need": 0.9, "today_active_count": 0,
        "unanswered_count": 0, "awaiting_reply": False,
        "last_active_ts": None, "last_real_reply": None,
    }
    s.update(kw)
    return s


def _cfg(**kw):
    c = dict(cfgmod.CONFIG_DEFAULTS)
    c.update(kw)
    return c


def test_all_gates_open_afternoon():
    cfg = _cfg()
    gates = state_machine.window_gates(_base(), cfg, datetime(2026, 8, 11, 14, 0))
    assert [g["gate"] for g in gates] == [
        "渴望足够", "精力在线", "不在勿扰时段", "过了冷却",
        "未达每日上限", "未回未超限", "允许深夜"]
    assert all(g["ok"] for g in gates)
    assert state_machine.should_open_window(_base(), cfg, datetime(2026, 8, 11, 14, 0))


def test_unanswered_max_names_the_blocker():
    gates = state_machine.window_gates(
        _base(unanswered_count=3, awaiting_reply=True),
        _cfg(), datetime(2026, 8, 11, 14, 0))
    assert not state_machine.should_open_window(
        _base(unanswered_count=3, awaiting_reply=True),
        _cfg(), datetime(2026, 8, 11, 14, 0))
    blocked = [g["gate"] for g in gates if not g["ok"]]
    # 值 = 封顶 3，要求 < 3 —— 明确告诉他卡在"没回消息一直催"上
    assert "未回未超限" in blocked
    g = next(g for g in gates if g["gate"] == "未回未超限")
    assert g["value"] == 3 and g["ok"] is False


def test_quiet_hour_marks_勿扰(tmp_path):
    gates = state_machine.window_gates(_base(), _cfg(), datetime(2026, 8, 11, 3, 0))
    assert any(not g["ok"] and g["gate"] == "不在勿扰时段" for g in gates)


def test_non_comment_tail_skips_comments(tmp_path):
    f = tmp_path / "hb.md"
    f.write_text("<!-- 注释 -->\n<!-- 空状态=无事可说 -->\n想你了。今天风很大。\n",
                encoding="utf-8")
    assert _non_comment_tail(f) == ["想你了。今天风很大。"]
    assert _non_comment_tail(tmp_path / "missing.md") == []
