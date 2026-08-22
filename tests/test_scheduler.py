"""scheduler.py — E3 时间自决（爱语协议移植）的解析 + 摄入 + 到点烧毁。"""
from datetime import datetime, timedelta
from active import scheduler as sched


# ---------- 解析 ----------

def test_parse_hhmm_next_occurrence_today():
    at = sched.parse_time_expression("20:00", datetime(2026, 8, 11, 12, 0))
    assert at == datetime(2026, 8, 11, 20, 0)


def test_parse_hhmm_past_rolls_to_tomorrow():
    at = sched.parse_time_expression("20:00", datetime(2026, 8, 11, 21, 30))
    assert at == datetime(2026, 8, 12, 20, 0)      # 那个钟点走了 → 等明天同一钟点


def test_parse_single_digit_hour():
    at = sched.parse_time_expression("8:05", datetime(2026, 8, 11, 7, 0))
    assert at == datetime(2026, 8, 11, 8, 5)


def test_parse_hhmm_invalid_clock():
    assert sched.parse_time_expression("25:00", datetime(2026, 8, 11, 12, 0)) is None
    assert sched.parse_time_expression("12:99", datetime(2026, 8, 11, 12, 0)) is None


def test_parse_relative_units():
    now = datetime(2026, 8, 11, 12, 0)
    assert sched.parse_time_expression("30min", now) == now + timedelta(minutes=30)
    assert sched.parse_time_expression("1h", now) == now + timedelta(hours=1)
    assert sched.parse_time_expression("90s", now) == now + timedelta(seconds=90)
    assert sched.parse_time_expression("2 小时", now) == now + timedelta(hours=2)
    assert sched.parse_time_expression("1.5 分钟", now) == now + timedelta(minutes=1.5)


def test_parse_garbage_returns_none():
    for bad in ("", "黄昏", "不约", "大概八点", "7:30 见", "abc", "半小时"):
        assert sched.parse_time_expression(bad, datetime(2026, 8, 11, 12, 0)) is None


# ---------- 摄入 / 到点 ----------

def test_consume_inbox_clears_and_stores(tmp_path):
    inbox = tmp_path / "schedule_in.md"
    store = tmp_path / "schedule.json"
    inbox.write_text("<!-- 注释头要跳过 -->\n20:00\n30min\n不是时刻\n",
                     encoding="utf-8")
    seen = sched.consume_inbox(cap=24, inbox=inbox, store=store,
                               now=datetime(2026, 8, 11, 12, 0))
    assert len(seen) == 2
    # 熟读即清：inbox 只剩注释头，非注释的时刻行全部取走
    rest = sched.read_inbox(inbox)
    assert "E3" in rest                       # 注释头保留，下次还能写
    assert all(line.lstrip().startswith("<!--") or not line.strip()
               for line in rest.splitlines())
    items = sched.pending(store)
    assert len(items) == 2
    assert {i["raw"] for i in items} == {"20:00", "30min"}
    assert items[0]["at"] < items[1]["at"]       # 按到期先后排队（30min 先到）


def test_pop_due_is_first_in_first_out(tmp_path):
    store = tmp_path / "schedule.json"
    sched.write_store([
        {"at": "2026-08-11T20:00:00", "raw": "20:00"},
        {"at": "2026-08-11T20:30:00", "raw": "20:30"},
    ], store)
    now = datetime(2026, 8, 11, 20, 10)
    assert sched.peek_due(now, store)["raw"] == "20:00"
    assert sched.pop_due(now, store)["raw"] == "20:00"     # 用完即焚
    assert sched.pending(store)[0]["raw"] == "20:30"       # 下一条还排着


def test_peek_due_none_before_time(tmp_path):
    store = tmp_path / "schedule.json"
    sched.write_store([{"at": "2026-08-11T20:00:00", "raw": "20:00"}], store)
    assert sched.peek_due(datetime(2026, 8, 11, 19, 0), store) is None
    assert sched.pop_due(datetime(2026, 8, 11, 19, 0), store) is None
    assert len(sched.pending(store)) == 1    # 没到点不乱烧


def test_consume_inbox_caps_at_limit(tmp_path):
    inbox = tmp_path / "schedule_in.md"
    store = tmp_path / "schedule.json"
    now = datetime(2026, 8, 11, 12, 0)
    inbox.write_text("\n".join(f"{i}min" for i in range(10)), encoding="utf-8")
    sched.consume_inbox(cap=4, inbox=inbox, store=store, now=now)
    items = sched.pending(store)
    assert len(items) == 4
    assert items[-1]["raw"] == "9min"        # 超上限只留最近 cap 条
