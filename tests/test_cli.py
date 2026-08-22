"""active/cli.py CLI 薄覆盖：pause/resume 信号 + tick 尊重暂停。
一律把 STATE / SEND_PATH 钉到 tmp；load_active_cfg 只读真 config（无写入）。"""
from active import cli, send_feed


def test_cmd_pause_writes_marker(monkeypatch, tmp_path):
    pt = tmp_path / "send_feed.md"
    monkeypatch.setattr(send_feed, "SEND_PATH", pt)
    captured = []
    monkeypatch.setattr(cli, "out", captured.append)
    assert cli.cmd_pause(None) == 0
    assert send_feed.pending_kinds(pt) == ["__PAUSE__"]
    assert "已写 __PAUSE__" in captured[0]


def test_cmd_resume_then_consume_clears(monkeypatch, tmp_path):
    pt = tmp_path / "send_feed.md"
    monkeypatch.setattr(send_feed, "SEND_PATH", pt)
    monkeypatch.setattr(cli, "out", lambda s: None)
    cli.cmd_pause(None)
    assert cli.cmd_resume(None) == 0
    assert send_feed.pending_kinds(pt) == ["__PAUSE__", "__RESUME__"]


def test_cmd_tick_reports_paused(monkeypatch, tmp_path):
    # __PAUSE__ 被 consume 落进状态后，tick 报 PAUSED 而不是谎报 OPEN
    monkeypatch.setattr(cli, "STATE", tmp_path / "state.json")
    pt = tmp_path / "send_feed.md"
    monkeypatch.setattr(send_feed, "SEND_PATH", pt)
    pt.write_text("__PAUSE__\n", encoding="utf-8")
    captured = []
    monkeypatch.setattr(cli, "out", captured.append)
    assert cli.cmd_tick(None) == 0
    assert "paused=True" in captured[0]      # consume 落了暂停
    assert "PAUSED" in captured[0]           # 窗口报告诚实标暂停


def test_cmd_tick_no_marker_reports_normal(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "STATE", tmp_path / "state.json")
    pt = tmp_path / "send_feed.md"
    monkeypatch.setattr(send_feed, "SEND_PATH", pt)
    pt.write_text("<!-- 无标记 -->\n", encoding="utf-8")
    captured = []
    monkeypatch.setattr(cli, "out", captured.append)
    cli.cmd_tick(None)
    assert "paused=False" in captured[0]
    assert "window=OPEN" in captured[0] or "window=close" in captured[0]
