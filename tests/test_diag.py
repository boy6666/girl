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
    # 2026-08-21 grill 拍板：只剩体内三扇（四扇卫门拆光）
    cfg = _cfg()
    gates = state_machine.window_gates(_base(), cfg, datetime(2026, 8, 11, 14, 0))
    assert [g["gate"] for g in gates] == ["渴望足够", "精力在线", "允许深夜"]
    assert all(g["ok"] for g in gates)
    assert state_machine.should_open_window(_base(), cfg, datetime(2026, 8, 11, 14, 0))


def test_removed_gates_gone_from_window_gates():
    names = {g["gate"] for g in
             state_machine.window_gates(_base(), _cfg(), datetime(2026, 8, 11, 14, 0))}
    for gone in ("不在勿扰时段", "过了冷却", "未达每日上限", "未回未超限"):
        assert gone not in names, f"{gone} 已被拆，不该出现在窗门里"


def test_quiet_hard_wall_gone_midnight():
    # 凌晨 3 点不再被勿扰硬墙挡（欲望足就能开；深夜软窗关掉才拦）
    cfg = _cfg()
    gates = state_machine.window_gates(_base(), cfg, datetime(2026, 8, 11, 3, 0))
    assert all(g["ok"] for g in gates)


def test_late_night_disabled_names_blocker():
    cfg = _cfg(allow_late_night=False)
    gates = state_machine.window_gates(_base(), cfg, datetime(2026, 8, 11, 3, 0))
    blocked = [g["gate"] for g in gates if not g["ok"]]
    assert blocked == ["允许深夜"]


def test_non_comment_tail_skips_comments(tmp_path):
    f = tmp_path / "hb.md"
    f.write_text("<!-- 注释 -->\n<!-- 空状态=无事可说 -->\n想你了。今天风很大。\n",
                encoding="utf-8")
    assert _non_comment_tail(f) == ["想你了。今天风很大。"]
    assert _non_comment_tail(tmp_path / "missing.md") == []
