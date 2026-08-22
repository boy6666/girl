"""send_feed 闭环：girl 每次真正发出去一条消息都记一行带类型标记——
__REPLY__ = 她在回主人的新消息（→ on_user_reply，清未回/断 awaiting/归零渴望）；
__SELF__  = 她自己主动发的（→ on_active_sent，记主动/冷却/awaiting/耗精力）。
心跳在这里消费：读到哪类就调对应状态变迁，然后清空。不靠后台猜、不靠她记性。
"""
from datetime import datetime

from active import config as cfgmod
from active import send_feed


def _base(**kw):
    s = {
        "initialized": True, "energy": 60.0, "mood": 0.2,
        "social_need": 0.9, "today_active_count": 0,
        "unanswered_count": 3, "awaiting_reply": True,
        "last_active_ts": "2026-08-12T17:48:37",
        "last_real_reply": "2026-08-12T18:00:00",
    }
    s.update(kw)
    return s


def _cfg(**kw):
    c = dict(cfgmod.CONFIG_DEFAULTS)
    c.update(kw)
    return c


def test_reply_marker_resets_await_and_clears(tmp_path):
    f = tmp_path / "send_feed.md"
    f.write_text("<!-- send feed -->\n__REPLY__\n", encoding="utf-8")
    now = datetime(2026, 8, 18, 12, 0)
    st, kinds = send_feed.consume(_base(), _cfg(), path=f, now=now)
    assert kinds == ["__REPLY__"]
    assert st["awaiting_reply"] is False
    assert st["unanswered_count"] == 0
    assert st["social_need"] == 0.0
    assert st["last_real_reply"] == now.isoformat(timespec="seconds")
    assert send_feed.has_pending(f) is False      # 文件被清空
    # 真回不应记"主动发"
    assert st["today_active_count"] == 0
    assert st["last_active_ts"] == "2026-08-12T17:48:37"


def test_self_marker_records_proactive_send(tmp_path):
    f = tmp_path / "send_feed.md"
    f.write_text("__SELF__\n", encoding="utf-8")
    now = datetime(2026, 8, 18, 14, 0)
    st, kinds = send_feed.consume(_base(), _cfg(), path=f, now=now)
    assert kinds == ["__SELF__"]
    assert st["today_active_count"] == 1
    assert st["last_active_ts"] == now.isoformat(timespec="seconds")
    assert st["awaiting_reply"] is True            # 主动发后在等他回
    assert st["social_need"] == 0.8                # 发≠被理，只小缓解
    assert st["energy"] == 52.0                    # 主动发耗精力
    # 主动发不碰"真回"相关字段
    assert st["unanswered_count"] == 3
    assert st["last_real_reply"] == "2026-08-12T18:00:00"


def test_reply_then_self_applied_in_order(tmp_path):
    f = tmp_path / "send_feed.md"
    f.write_text("__REPLY__\n__SELF__\n", encoding="utf-8")
    now = datetime(2026, 8, 18, 14, 0)
    st, kinds = send_feed.consume(_base(), _cfg(), path=f, now=now)
    # 顺序保留：先真回（清未回/断 awaiting），后主动（再 awaiting，记一次主动）
    assert kinds == ["__REPLY__", "__SELF__"]
    assert st["unanswered_count"] == 0
    assert st["today_active_count"] == 1
    assert st["awaiting_reply"] is True
    assert st["last_real_reply"] == now.isoformat(timespec="seconds")


def test_empty_or_comment_file_is_noop(tmp_path):
    f = tmp_path / "send_feed.md"
    f.write_text("<!-- only a comment -->\n", encoding="utf-8")
    st, kinds = send_feed.consume(_base(), _cfg(), path=f)
    assert kinds == []
    assert st["awaiting_reply"] is True
    assert st["unanswered_count"] == 3


def test_missing_file_is_noop(tmp_path):
    st = _base()
    st2, kinds = send_feed.consume(st, _cfg(), path=tmp_path / "none.md")
    assert kinds == []
    assert st2 == st


def test_reply_no_longer_gated_by_unanswered(tmp_path):
    # 2026-08-21 grill 拍板：未回未超限拆了，真回后不靠它放行，窗门里根本没它
    from active import state_machine
    f = tmp_path / "send_feed.md"
    f.write_text("__REPLY__\n", encoding="utf-8")
    now = datetime(2026, 8, 18, 14, 0)
    cfg = _cfg()
    st, _ = send_feed.consume(_base(), cfg, path=f, now=now)
    names = [g["gate"] for g in state_machine.window_gates(st, cfg, now)]
    assert "未回未超限" not in names
    # 真回后 awaiting 松开；渴望再涨上来到点 → 阈值路径照开
    st2 = dict(st)
    st2["social_need"] = 0.9
    assert state_machine.should_open_window(st2, cfg, now)
