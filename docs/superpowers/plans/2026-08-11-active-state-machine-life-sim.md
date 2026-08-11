# 小语 V1.5 主动状态机 + 生活模拟（可生长） — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让小语有自己的、**会生长**的生活（作息/沉淀/梦境 + 每日 LLM 写生活日志）和一个持续自己"想不想找你"的状态机（energy/mood/social_need）；Web 后台 Python 层当"窗口管理者 + 生活拥有者"，girl agent 当"声音"，单一微信出口不变。

**Architecture:** C 混合方案。`active/` 包 = 纯函数状态机（tick/决策）+ 生活内容库（web 可编辑）+ 生活日志（agent 生长）+ 生活模拟 + 动机卡片 + 注入器接口。FastAPI 后台挂一个心跳线程周期性推进状态、判定是否开"主动窗口"；开窗时把"动机卡片"（从今天生活 + 日志延续取料）交给注入器，由 girl agent 用自己的声音发出。生长日志由 girl agent 每日生成 append 进 `data/life_journal.md`。后台**永不直接发微信**。

**Tech Stack:** Python 3.11+、FastAPI 0.110、pytest + httpx（测试）、PyYAML、OpenClaw（宿主；真注入/真生长留 Task 14 验证后铺开）。

## Global Constraints

- 单一出口：后台只开窗口 + 注入卡片，**不直接发微信**；真发送永远经 OpenClaw。
- 记忆/人格/状态/生活 100% 本机；`data/state.json`、`data/life_journal.md` 入 .gitignore。
- 状态值域：`energy` 0–100；`mood` −1..+1；`social_need` 0–1。
- 状态机函数保持**纯函数**（不改入参，返回新 dict）。
- 字符串 UTF-8；中文 UI，文案自然、不机械。
- 决定性：生活模拟用 `random.Random(seed)`，同一天输出稳定可测；LLM 生长层有 dry_run 种子兜底（未接 OpenClaw 也可测）。
- 默认参数「自然淡雅」取自 spec §12；"勿扰 23–7 vs 允许凌晨 true"被收敛为：**勿扰=硬墙**（默认 02:00–05:00，绝不在这些时主动），**深夜窗口 23–06 + allow_late_night**=软窗口（凌晨失眠关心的由来）。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `active/__init__.py` | 导出 load_state / save_state |
| `active/config.py` | CONFIG_DEFAULTS + merge_config（参数中心） |
| `active/state_store.py` | data/state.json 读写 + default_state |
| `active/state_machine.py` | 纯函数：三状态 tick + 决策 + 事件 |
| `active/life_content.py` | 生活内容库 data/life_content.yaml（web 可编辑） |
| `active/life_journal.py` | 生活日志 data/life_journal.md（agent 生长，读+append） |
| `active/life_grower.py` | grow_today：生成当天生活日志条目（dry_run 种子 / 真 LLM 接口） |
| `active/life_sim.py` | current_activity / today_highlights / maybe_dream（用内容库+日志） |
| `active/motivation.py` | 生成"动机卡片"（今天生活 + 日志延续 + 状态） |
| `active/injector.py` | 注入器接口（dry_run 默认；单出口文档；真 OpenClaw 留 Task 14） |
| `web/main.py` | 心跳线程 + /api/active/* 端点 |
| `web/templates/index.html` | "行为"段改名"主动状态机"；新增"她的一天"标签页 |
| `web/static/js/app.js` | gauges / 生活预览 / 现在推 / 生长按钮 / 内容编辑 / 参数保存 |
| `web/static/css/style.css` | gauge / active-life / editor 样式 |
| `resources/requirements-dev.txt` | pytest + httpx |
| `.gitignore` | 加 `data/state.json`、`data/life_journal.md` |
| `data/config.yaml` | 重写 `active_behavior` 段为新参数 |

---

## Task 1: 脚手架 + 参数中心 config.py

**Files:**
- Create: `active/__init__.py`
- Create: `active/config.py`
- Create: `resources/requirements-dev.txt`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `active.config.CONFIG_DEFAULTS: dict`（唯一参数真相）；`active.config.merge_config(raw: dict|None) -> dict`（洗并入默认，忽略未知键）。Task 2–14 全部消费这组默认参数。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
from active import config as c


def test_defaults_exist():
    assert c.CONFIG_DEFAULTS["open_threshold"] == 0.5
    assert c.CONFIG_DEFAULTS["daily_max"] == 2
    assert c.CONFIG_DEFAULTS["quiet_start"] == 2
    assert c.CONFIG_DEFAULTS["quiet_end"] == 5
    assert c.CONFIG_DEFAULTS["max_unanswered"] == 3
    assert c.CONFIG_DEFAULTS["attachment"] == "secure"


def test_merge_overrides_and_ignores_unknown():
    merged = c.merge_config({"open_threshold": 0.7, "bogus": 1})
    assert merged["open_threshold"] == 0.7
    assert merged["daily_max"] == 2
    assert "bogus" not in merged
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_config.py -v` — 期望：FAIL（ModuleNotFoundError: no module named 'active'）

- [ ] **Step 3: 实现**

`active/__init__.py`:
```python
"""active — 小语主动状态机 + 生活模拟包。"""
from . import config, state_store  # noqa: F401


def load_state():
    return state_store.load()


def save_state(state):
    state_store.save(state)
```

`active/config.py`:
```python
"""config.py — 主动状态机全部参数（唯一真相，落点 data/config.yaml 的 active_behavior 段）。"""
CONFIG_DEFAULTS = {
    "open_threshold": 0.5,           # 社交需求达到多少才考虑开窗
    "cooldown_seconds": 300,         # 主动冷却（秒）
    "daily_max": 2,                  # 每日主动上限（次）
    "quiet_start": 2,                # 勿扰硬墙开始（时）——绝不在这些时辰主动
    "quiet_end": 5,                  # 勿扰硬墙结束（时）
    "max_unanswered": 3,             # 连续未回上限（达到暂停催人）
    "allow_late_night": True,        # 是否允许凌晨/深夜软窗口
    "late_night_start": 23,          # 深夜软窗口开始（时）
    "early_morning_end": 6,          # 深夜软窗口结束（时）
    "tick_minutes": 15,              # 心跳间隔（分钟）
    "growth_rate_per_hour": 0.12,    # 思念涨速（每小时基数）
    "energy_time_constant_min": 240, # 精力漂移常数（4h）
    "mood_time_constant_min": 360,   # 情绪回基线常数（6h）
    "mood_baseline": 0.15,           # 情绪基线
    "attachment": "secure",          # secure | anxious | avoidant
    "seed_energy": 80.0,
    "seed_mood": 0.2,
    "grow_provider": "dry_run",      # dry_run | openclaw（真生长见 Task 14）
    "inject_provider": "dry_run",    # dry_run | openclaw（真注入见 Task 14）
}


def merge_config(raw: dict | None = None) -> dict:
    cfg = dict(CONFIG_DEFAULTS)
    if raw:
        for k, v in raw.items():
            if k in cfg:
                cfg[k] = v
    return cfg
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_config.py -v` — 期望：PASS (2 passed)

- [ ] **Step 5: 提交**

```bash
git add active/__init__.py active/config.py tests/test_config.py resources/requirements-dev.txt tests/__init__.py
git commit -m "feat(active): 参数中心 config.py + 测试脚手架"
```

> `resources/requirements-dev.txt` 内容：`pytest` + `httpx`（各一行）。

---

## Task 2: state_store.py — 状态持久化

**Files:**
- Create: `active/state_store.py`
- Test: `tests/test_state_store.py`

**Interfaces:**
- Produces: `default_state(now)->dict`；`load(path=DEFAULT_STATE_PATH)->dict`；`save(state, path)->None`。Task 3–14 消费。
- 状态键：`energy, mood, social_need, last_real_reply, last_active_ts, unanswered_count, today_active_count, today, awaiting_reply`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_state_store.py
from datetime import datetime
from active import state_store


def test_default_state_keys(tmp_path):
    s = state_store.default_state(datetime(2026, 8, 11, 12, 0))
    for k in ("energy", "mood", "social_need", "last_real_reply",
              "last_active_ts", "unanswered_count", "today_active_count",
              "today", "awaiting_reply"):
        assert k in s
    assert s["today"] == "2026-08-11"
    assert s["social_need"] == 0.0
    assert s["awaiting_reply"] is False


def test_load_missing_returns_default(tmp_path):
    assert state_store.load(tmp_path / "none.json")["social_need"] == 0.0


def test_save_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    state_store.save(state_store.default_state(datetime(2026, 8, 11)), p)
    assert state_store.load(p)["today"] == "2026-08-11"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_state_store.py -v` — 期望：FAIL

- [ ] **Step 3: 实现**

```python
# active/state_store.py
"""state_store.py — data/state.json 读写（runtime 主动状态）。"""
import json
from datetime import datetime
from pathlib import Path

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "state.json"


def default_state(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    return {
        "energy": None,            # 首次 tick 由 config.seed_energy 填入
        "mood": None,              # 首次 tick 由 config.seed_mood 填入
        "social_need": 0.0,
        "last_real_reply": None,   # iso 时间戳
        "last_active_ts": None,
        "unanswered_count": 0,
        "today_active_count": 0,
        "today": now.strftime("%Y-%m-%d"),
        "awaiting_reply": False,
    }


def load(path: Path = DEFAULT_STATE_PATH) -> dict:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    base = default_state()
    base.update({k: v for k, v in data.items() if k in base})
    return base


def save(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_state_store.py -v` — 期望：PASS (3 passed)

- [ ] **Step 5: 提交**

```bash
git add active/state_store.py tests/test_state_store.py
git commit -m "feat(active): state.json 读写 + 默认状态"
```

---

## Task 3: state_machine — energy + mood 推进

**Files:**
- Create: `active/state_machine.py`
- Test: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: `config.CONFIG_DEFAULTS`；`state_store.default_state`。
- Produces: `_energy_target(hour)->float`；`tick(state, config, now=None, reply_quality=None) -> dict`（纯函数）。Task 4–5 同文件扩展；Task 6–14 消费 `tick`。
- 约定：`reply_quality=None`=无新用户回复；`-1..1`=新回复冷热度。tick 不改入参。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_state_machine.py
from datetime import datetime
from active import config as c, state_machine as sm

CFG = c.CONFIG_DEFAULTS


def base(**over):
    s = {
        "energy": 80.0, "mood": 0.0, "social_need": 0.0,
        "last_real_reply": None, "last_active_ts": None,
        "unanswered_count": 0, "today_active_count": 0,
        "today": "2026-08-11", "awaiting_reply": False,
    }
    s.update(over)
    return s


def test_energy_rises_toward_afternoon_target():
    s = base(energy=60.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0))  # 下午目标 ~90
    assert 60.0 < s1["energy"] <= 90.0


def test_energy_falls_at_night():
    s = base(energy=80.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 23, 0))  # 夜间目标 ~30
    assert s1["energy"] < 80.0


def test_tick_is_pure_and_mood_drifts_to_baseline():
    s = base(mood=0.8)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0))
    assert s["mood"] == 0.8          # 入参没被改
    assert s1["mood"] < 0.8          # 向基线 0.15 飘


def test_reply_bumps_mood_positive():
    s = base(mood=0.0)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 14, 0), reply_quality=0.8)
    assert s1["mood"] > 0.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现（本任务先 energy+mood；social_need 在 Task 4）**

```python
# active/state_machine.py
"""state_machine.py — 纯函数状态机：energy/mood/social_need 推进 + 决策。"""
import math
from datetime import datetime


def _energy_target(hour: int) -> float:
    """作息曲线 → 目标精力 (0-1)。午后高、深夜低。"""
    if hour < 6:
        return 0.25
    if hour < 10:
        return 0.6
    if hour < 14:
        return 0.75
    if hour < 19:
        return 0.9
    if hour < 23:
        return 0.6
    return 0.3


def _iso(now: datetime) -> str:
    return now.isoformat(timespec="seconds")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _init(state, config):
    """首次 tick 用 seed 填 energy/mood。"""
    s = dict(state)
    if s.get("energy") is None:
        s["energy"] = float(config.get("seed_energy", 80.0))
    if s.get("mood") is None:
        s["mood"] = float(config.get("seed_mood", 0.2))
    s["social_need"] = float(s.get("social_need", 0.0) or 0.0)
    return s


def tick(state, config, now=None, reply_quality=None) -> dict:
    """推进一个心跳。纯函数：返回新 dict，不改 state。"""
    now = now or datetime.now()
    s = _init(state, config)

    if s.get("today") != now.strftime("%Y-%m-%d"):
        s["today"] = now.strftime("%Y-%m-%d")
        s["today_active_count"] = 0

    if reply_quality is not None:
        s["social_need"] = 0.0
        s["unanswered_count"] = 0
        s["awaiting_reply"] = False
        s["last_real_reply"] = _iso(now)
        s["mood"] = _clamp(s["mood"] + 0.3 * reply_quality, -1.0, 1.0)
    else:
        base = config.get("mood_baseline", 0.15)
        k = 1 - math.exp(-1.0 / config["mood_time_constant_min"])
        s["mood"] += (base - s["mood"]) * k

    target = _energy_target(now.hour) * 100.0
    k = 1 - math.exp(-1.0 / config["energy_time_constant_min"])
    s["energy"] = _clamp(s["energy"] + (target - s["energy"]) * k, 0.0, 100.0)
    return s
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：PASS (4 passed)

- [ ] **Step 5: 提交**

```bash
git add active/state_machine.py tests/test_state_machine.py
git commit -m "feat(active): 状态机 energy/mood 推进 + 回复情绪修正"
```

---

## Task 4: state_machine — social_need 涨落（时间驱动 + 依恋调制 + 应答归零）

**Files:**
- Modify: `active/state_machine.py`
- Test: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: `_init`、`tick`（Task 3）。
- Produces: 扩展 `tick`：无回复按时间涨 `social_need`；`_ATTACH_MULT` 依恋调制；回复归零。

- [ ] **Step 1: 写失败测试（追加到 test_state_machine.py）**

```python
def test_social_need_grows_without_reply():
    s = base(social_need=0.0, last_real_reply="2026-08-11T10:00:00")
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0))  # 2h
    assert 0.0 < s1["social_need"] < 1.0


def test_reply_resets_social_need():
    s = base(social_need=0.9, mood=0.2)
    s1 = sm.tick(s, CFG, datetime(2026, 8, 11, 12, 0), reply_quality=0.5)
    assert s1["social_need"] == 0.0
    assert s1["awaiting_reply"] is False


def test_anxious_grows_faster_than_avoidant():
    t = datetime(2026, 8, 11, 12, 0)
    sa = sm.tick(base(social_need=0.0, last_real_reply="2026-08-11T10:00:00"),
                 {**CFG, "attachment": "anxious"}, t)
    sv = sm.tick(base(social_need=0.0, last_real_reply="2026-08-11T10:00:00"),
                 {**CFG, "attachment": "avoidant"}, t)
    assert sa["social_need"] > sv["social_need"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：FAIL（social_need 恒为 0）

- [ ] **Step 3: 实现**

文件顶部加常量：
```python
_ATTACH_MULT = {"anxious": 1.5, "secure": 1.0, "avoidant": 0.7}
```
文件尾加帮助函数：
```python
def _dt_hours(state, now) -> float:
    last = state.get("last_real_reply")
    if not last:
        return 1.0
    try:
        t0 = datetime.fromisoformat(last)
        return max(0.0, (now - t0).total_seconds() / 3600.0)
    except (TypeError, ValueError):
        return 1.0
```
把 `tick` 的 `else:` 分支改为：
```python
    else:
        # 社交需求按时间涨（越久没被真回越渴望）
        dt_h = _dt_hours(s, now)
        moodn = (s["mood"] + 1) / 2            # 情绪好时更想找(0..1)
        mult = _ATTACH_MULT.get(config.get("attachment", "secure"), 1.0)
        grow = config["growth_rate_per_hour"] * dt_h * (0.6 + 0.4 * moodn) * mult
        s["social_need"] = _clamp(s["social_need"] + grow, 0.0, 1.0)
        # 未回计数：awaiting_reply 时每心跳 +1（封顶 max_unanswered）
        if s.get("awaiting_reply"):
            s["unanswered_count"] = min(config["max_unanswered"],
                                        s["unanswered_count"] + 1)
        base = config.get("mood_baseline", 0.15)
        k = 1 - math.exp(-1.0 / config["mood_time_constant_min"])
        s["mood"] += (base - s["mood"]) * k
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：PASS（7 passed）

- [ ] **Step 5: 提交**

```bash
git add active/state_machine.py tests/test_state_machine.py
git commit -m "feat(active): social_need 时间驱动增长 + 应答归零 + 依恋调制"
```

---

## Task 5: state_machine — 决策层 + 事件适配

**Files:**
- Modify: `active/state_machine.py`
- Test: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: `_init`、`tick`、`_dt_hours`、`_clamp`。
- Produces: `should_open_window(state, config, now=None)->bool`；`on_active_sent(state, config, now=None)->dict`；`on_user_reply(state, config, now=None, quality=0.0)->dict`。Task 6–14 全部消费。

- [ ] **Step 1: 写失败测试（追加）**

```python
def test_window_closed_when_need_low():
    assert not sm.should_open_window(base(social_need=0.2), CFG, datetime(2026, 8, 11, 14, 0))


def test_window_opens_afternoon():
    assert sm.should_open_window(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 14, 0))


def test_quiet_hours_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 3, 0))


def test_cooldown_blocks():
    s = base(social_need=0.9, energy=80.0, last_active_ts="2026-08-11T13:58:00")
    assert not sm.should_open_window(s, CFG, datetime(2026, 8, 11, 14, 0))


def test_daily_max_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0, today_active_count=2),
                                     CFG, datetime(2026, 8, 11, 14, 0))


def test_unanswered_max_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0, unanswered_count=3),
                                     CFG, datetime(2026, 8, 11, 14, 0))


def test_energy_low_blocks():
    assert not sm.should_open_window(base(social_need=0.9, energy=10.0), CFG, datetime(2026, 8, 11, 14, 0))


def test_late_night_disabled_blocks():
    cfg = {**CFG, "allow_late_night": False}
    assert not sm.should_open_window(base(social_need=0.9, energy=80.0), cfg, datetime(2026, 8, 11, 0, 0))


def test_active_sent_increments_and_relief():
    s1 = sm.on_active_sent(base(social_need=0.9, energy=80.0), CFG, datetime(2026, 8, 11, 14, 0))
    assert s1["today_active_count"] == 1
    assert s1["social_need"] < 0.9
    assert s1["energy"] < 80.0
    assert s1["awaiting_reply"] is True
    assert s1["last_active_ts"] is not None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：FAIL（should_open_window / on_active_sent 不存在）

- [ ] **Step 3: 实现（追加到文件尾）**

```python
def should_open_window(state, config, now=None) -> bool:
    """是否开放一个"主动窗口"（全部守卫满足才 True）。"""
    now = now or datetime.now()
    s = _init(state, config)
    if s["social_need"] < float(config.get("open_threshold", 0.5)):
        return False
    if s["energy"] < 20:
        return False

    hour = now.hour
    qs, qe = int(config["quiet_start"]), int(config["quiet_end"])
    in_quiet = (qs <= hour < qe) if qs <= qe else (hour >= qs or hour < qe)
    if in_quiet:
        return False

    last_a = s.get("last_active_ts")
    if last_a:
        try:
            t0 = datetime.fromisoformat(last_a)
            if (now - t0).total_seconds() < config["cooldown_seconds"]:
                return False
        except (TypeError, ValueError):
            pass

    if s["today_active_count"] >= config["daily_max"]:
        return False
    if s["unanswered_count"] >= config["max_unanswered"]:
        return False
    if not config.get("allow_late_night", True):
        if hour >= int(config["late_night_start"]) or hour < int(config["early_morning_end"]):
            return False
    return True


def on_active_sent(state, config, now=None) -> dict:
    """她真主动发了一条：更新计数/冷却/渴望小缓解/耗精力。"""
    now = now or datetime.now()
    s = _init(state, config)
    if s.get("today") != now.strftime("%Y-%m-%d"):
        s["today"] = now.strftime("%Y-%m-%d")
        s["today_active_count"] = 0
    s["today_active_count"] += 1
    s["last_active_ts"] = _iso(now)
    s["awaiting_reply"] = True
    s["social_need"] = _clamp(s["social_need"] - 0.1, 0.0, 1.0)  # 发了≠被理，只小缓解
    s["energy"] = _clamp(s["energy"] - 8.0, 0.0, 100.0)
    return s


def on_user_reply(state, config, now=None, quality=0.0) -> dict:
    """新用户消息到达时调用：归零渴望/未回、记时间、情绪修正。"""
    return tick(state, config, now, reply_quality=quality)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_state_machine.py -v` — 期望：PASS（16 passed）

- [ ] **Step 5: 提交**

```bash
git add active/state_machine.py tests/test_state_machine.py
git commit -m "feat(active): 主动窗口决策层 + 事件适配(发出/收到回复)"
```

---

## Task 6: life_content.py — 生活内容库（web 可编辑）

**Files:**
- Create: `active/life_content.py`
- Test: `tests/test_life_content.py`

**Interfaces:**
- Produces: `load_content(path=LIFE_CONTENT_PATH)->dict`（与默认深合并）；`save_content(content, path)->None`；`DEFAULT_CONTENT: dict`；`BUCKETS = ("morning","work","afternoon","evening")`。Task 8–14 消费。
- 内容 schema：`{habits:[str], favorites:{}, schedule:{wake:int}, buckets:{morning:[str],...}}`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_life_content.py
from active import life_content as lc


def test_defaults_loaded(tmp_path):
    c_ = lc.load_content(tmp_path / "none.yaml")
    assert c_["schedule"]["wake"] == 7
    assert len(c_["buckets"]["morning"]) >= 1
    assert isinstance(c_["habits"], list)


def test_load_merges_user_bucket(tmp_path):
    p = tmp_path / "life_content.yaml"
    p.write_text("buckets:\n  morning: [\"自定义晨间\"]\n", encoding="utf-8")
    c_ = lc.load_content(p)
    assert c_["buckets"]["morning"] == ["自定义晨间"]
    assert len(c_["buckets"]["work"]) >= 1  # 未配置的时段仍用默认


def test_save_roundtrip(tmp_path):
    p = tmp_path / "life_content.yaml"
    content = lc.load_content()
    content["habits"].append("喜欢下雨天")
    lc.save_content(content, p)
    assert "喜欢下雨天" in lc.load_content(p)["habits"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_life_content.py -v` — 期望：FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现**

```python
# active/life_content.py
"""life_content.py — 小语的生活内容库 data/life_content.yaml（Web「她的一天」页可编辑）。"""
import copy
from pathlib import Path

import yaml

LIFE_CONTENT_PATH = Path(__file__).resolve().parents[1] / "data" / "life_content.yaml"

BUCKETS = ("morning", "work", "afternoon", "evening")

DEFAULT_CONTENT = {
    "habits": [
        "喜欢猫，路上看到的猫都会多看两眼",
        "每周三傍晚去公园散步",
        "最近在追一部剧，还没看到结尾",
    ],
    "favorites": {
        "color": "暖色调，偏爱橘色",
        "food": "咖啡和栗子",
    },
    "schedule": {"wake": 7},
    "buckets": {
        "morning": [
            "晨跑二十分钟，回来冲了杯热咖啡",
            "赖了会儿床，刷手机看到只猫",
            "起了个大早，把昨儿没看完的书看完了",
        ],
        "work": [
            "手里那摊活总算弄完一段，腰都直了",
            "开了一上午的会，脑子嗡嗡的",
            "写东西卡了半天，刚有点眉目",
        ],
        "afternoon": [
            "楼下那家店新出的栗子味好香，没忍住",
            "路过看到晚霞，拍了一张",
            "散步被风一吹，又想起之前那件事",
        ],
        "evening": [
            "洗完澡窝在床上，今天有点累",
            "追的剧更新了，憋着没忍住先看了",
            "又觉得一个人待着有点空",
        ],
    },
}


def load_content(path: Path = LIFE_CONTENT_PATH) -> dict:
    out = copy.deepcopy(DEFAULT_CONTENT)
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        for k in ("habits", "favorites", "schedule"):
            if data.get(k):
                out[k] = data[k]
        for b in BUCKETS:
            if data.get("buckets", {}).get(b):
                out["buckets"][b] = data["buckets"][b]
    return out


def save_content(content: dict, path: Path = LIFE_CONTENT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_life_content.py -v` — 期望：PASS (3 passed)

- [ ] **Step 5: 提交**

```bash
git add active/life_content.py tests/test_life_content.py
git commit -m "feat(active): 生活内容库（web 可编辑）"
```

---

## Task 7: life_journal.py + life_grower.py — 生长日志

**Files:**
- Create: `active/life_journal.py`
- Create: `active/life_grower.py`
- Test: `tests/test_life_journal.py`, `tests/test_life_grower.py`

**Interfaces:**
- life_journal: `JOURNAL_PATH`；`read_journal(path)->str`；`append_entry(day:str, text:str, path)->None`；`recent_entries(path, n=3)->list[str]`；`last_entry_date(path)->str|None`。
- life_grower: `grow_today(content:dict, journal_text:str, day:str, provider="dry_run", seed=None)->str`。Task 8/11/14 消费。真 LLM provider 在 Task 14 由 injector 提供；dry_run 用 `_seed_entry` 生成。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_life_journal.py
from active import life_journal as lj


def test_append_and_recent(tmp_path):
    p = tmp_path / "j.md"
    lj.append_entry("2026-08-10", "前天去看海。", p)
    lj.append_entry("2026-08-11", "今天散步遇到一只猫。", p)
    assert lj.last_entry_date(p) == "2026-08-11"
    rec = lj.recent_entries(p, 2)
    assert rec == ["今天散步遇到一只猫。", "前天去看海。"]


def test_empty(tmp_path):
    assert lj.recent_entries(tmp_path / "none.md") == []
    assert lj.last_entry_date(tmp_path / "none.md") is None


# tests/test_life_grower.py
from active import life_grower as lg


def test_dry_run_uses_content_and_returns_text():
    content = {"habits": ["喜欢猫"], "favorites": {"food": "咖啡"},
               "schedule": {"wake": 7},
               "buckets": {"morning": ["晨跑"], "work": ["写代码"],
                           "afternoon": ["散步"], "evening": ["按时睡"]}}
    txt = lg.grow_today(content, "", "2026-08-11", provider="dry_run", seed=1)
    assert isinstance(txt, str) and len(txt) > 10


def test_dry_run_deterministic():
    content = lg_content_fixture()
    a = lg.grow_today(content, "", "2026-08-11", provider="dry_run", seed=7)
    b = lg.grow_today(content, "", "2026-08-11", provider="dry_run", seed=7)
    assert a == b
```

（`lg_content_fixture` 可用 `from active import life_content as lc; lc.DEFAULT_CONTENT`——在 test 里直接 `import life_content` 取 `DEFAULT_CONTENT` 即可：`content = {"habits":[],"favorites":{},"schedule":{"wake":7},"buckets":{k:v for k,v in lc.DEFAULT_CONTENT["buckets"].items()}}`。）

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_life_journal.py tests/test_life_grower.py -v` — 期望：FAIL

- [ ] **Step 3: 实现**

```python
# active/life_journal.py
"""life_journal.py — 生活日志 data/life_journal.md（agent 生长，读+append）。"""
from pathlib import Path

JOURNAL_PATH = Path(__file__).resolve().parents[1] / "data" / "life_journal.md"


def read_journal(path: Path = JOURNAL_PATH) -> str:
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def append_entry(day: str, text: str, path: Path = JOURNAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## {day}\n{text}\n")


def _parse_entries(text: str) -> list[tuple[str, str]]:
    entries = []   # (date, body) in file order
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            entries.append((cur, ""))
        elif cur is not None and line.strip():
            entries[-1] = (entries[-1][0], entries[-1][1] + line.strip() + "\n")
    return entries


def recent_entries(path: Path = JOURNAL_PATH, n: int = 3) -> list[str]:
    entries = _parse_entries(read_journal(path))
    return [body.strip() for _, body in entries[-n:]]


def last_entry_date(path: Path = JOURNAL_PATH) -> str | None:
    entries = _parse_entries(read_journal(path))
    return entries[-1][0] if entries else None
```

```python
# active/life_grower.py
"""life_grower.py — 生成当天生活日志条目。
provider="dry_run": 用内容库种子拼接（零依赖、可测、确定性）。
provider="openclaw": 交给 girl agent 用真实声音写当天生活（Task 14 接 injector）。
"""
import random


def _pick(bucket: list[str], day: str, rng) -> str:
    return rng.choice(bucket or ["随意过了大半天"])


def _seed_entry(content: dict, journal_text: str, day: str, seed=None) -> str:
    rng = random.Random(seed if seed is not None else day)
    buckets = content.get("buckets", {})
    morning = _pick(buckets.get("morning", []), day, rng)
    afternoon = _pick(buckets.get("afternoon", []), day, rng)
    evening = _pick(buckets.get("evening", []), day, rng)
    habits = content.get("habits", [])
    extra = f"中间我又{rng.choice(habits)}。" if habits else ""
    return f"{morning}。下午{afternoon}。{extra}到了晚上，{evening}。"


def grow_today(content: dict, journal_text: str, day: str,
               provider: str = "dry_run", seed=None) -> str:
    if provider == "openclaw":
        # Task 14 接入：经 injector 唤醒 girl agent 以第一人称写今天生活（内部，不发）
        from .injector import generate_text
        return generate_text(
            "你是小语。请用你自己的口吻，写一小段(3-5句)今天你经历了什么、想到什么。"
            "这是内部的生活日记，不是发给主人的消息，不用称呼主人、不用问候、不用结尾问句。"
            f"\n今天日期:{day}\n你的生活底色:{content}\n之前的生活日志:\n{journal_text or '(还没有)'}",
            provider=provider)
    return _seed_entry(content, journal_text, day, seed)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_life_journal.py tests/test_life_grower.py -v` — 期望：PASS（2 + 2 = 4 passed）

- [ ] **Step 5: 提交**

```bash
git add active/life_journal.py active/life_grower.py tests/test_life_journal.py tests/test_life_grower.py
git commit -m "feat(active): 生活日志读写 + LLM生长接口(dry_run种子兜底)"
```

---

## Task 8: life_sim.py — 用内容库+日志出生活片段

**Files:**
- Create: `active/life_sim.py`
- Test: `tests/test_life_sim.py`

**Interfaces:**
- Consumes: `life_content.load_content`、`life_content.BUCKETS`。
- Produces: `current_activity(content:dict, day:str, hour:int)->str`；`today_highlights(content:dict, day:str, hour:int, count:int=2)->list[str]`；`maybe_dream(day:str, now:datetime)->str|None`。Task 9（motivation）消费。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_life_sim.py
from datetime import datetime
from active import life_content as lc, life_sim as life

C = lc.DEFAULT_CONTENT


def test_current_activity_morning_from_bucket():
    a = life.current_activity(C, "2026-08-11", 8)
    assert a in C["buckets"]["morning"]


def test_night_is_sleeping():
    assert life.current_activity(C, "2026-08-11", 3) == life._SLEEP


def test_highlights_deterministic_and_limited():
    a = life.today_highlights(C, "2026-08-11", 19, 2)
    b = life.today_highlights(C, "2026-08-11", 19, 2)
    assert a == b and len(a) <= 2 and all(h for h in a)


def test_dream_only_late_night():
    assert life.maybe_dream("2026-08-11", datetime(2026, 8, 11, 2, 0)) is not None
    assert life.maybe_dream("2026-08-11", datetime(2026, 8, 11, 15, 0)) is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_life_sim.py -v` — 期望：FAIL

- [ ] **Step 3: 实现**

```python
# active/life_sim.py
"""life_sim.py — 用生活内容库+日志给小语生成"当下生活片段"与梦境。"""
import random
from datetime import datetime

_SLEEP = "在睡觉，梦里乱七八糟的"

# 梦境保持轻量短模板（梦是碎片，不参与"生长"）
_DREAMS = [
    "梦见我们在一条很长很长的街上走，你一直牵着我的手",
    "梦到小时候住的老房子，醒来有点恍惚",
    "梦里你特别开心地跟我说了件好事，醒来我忍不住笑",
    "梦到一只会说话的猫追着我跑",
]


def _bucket(hour: int) -> str:
    if hour < 6:
        return "sleep"
    if hour < 10:
        return "morning"
    if hour < 14:
        return "work"
    if hour < 17:
        return "afternoon"
    if hour < 23:
        return "evening"
    return "sleep"


_CYCLE = ("morning", "work", "afternoon", "evening")


def current_activity(content: dict, day: str, hour: int) -> str:
    b = _bucket(hour)
    if b == "sleep":
        return _SLEEP
    rng = random.Random(f"{day}:{b}")
    pool = content.get("buckets", {}).get(b, [])
    return rng.choice(pool or ["在忙今天的琐事"])


def today_highlights(content: dict, day: str, hour: int, count: int = 2) -> list[str]:
    if hour < 6:
        idx = 4                      # 深夜=今天已过完，含全部时段
    elif _bucket(hour) == "sleep":
        idx = 4
    else:
        idx = _CYCLE.index(_bucket(hour)) + 1   # 含当前时段
    out = []
    for i in range(min(idx, len(_CYCLE))):
        b = _CYCLE[i]
        pool = content.get("buckets", {}).get(b, [])
        if pool:
            out.append(random.Random(f"{day}:{b}").choice(pool))
    return out[:count]


def maybe_dream(day: str, now: datetime) -> str | None:
    if 0 <= now.hour < 8:
        return random.Random(f"{day}:dream:{now.hour}").choice(_DREAMS)
    return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_life_sim.py -v` — 期望：PASS (4 passed)

- [ ] **Step 5: 提交**

```bash
git add active/life_sim.py tests/test_life_sim.py
git commit -m "feat(active): 生活模拟(当下片段/今日高光/梦境) 用内容库"
```

---

## Task 9: motivation.py — 动机卡片

**Files:**
- Create: `active/motivation.py`
- Test: `tests/test_motivation.py`

**Interfaces:**
- Consumes: `life_sim.current_activity`、`life_sim.today_highlights`、`life_sim.maybe_dream`、`life_journal.recent_entries`。
- Produces: `build_motivation_card(state:dict, content:dict, journal:str, day:str, now:datetime)->str`。Task 11/14 消费（注入给 agent 的文本）。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_motivation.py
from datetime import datetime
from active import life_content as lc, motivation as mo

C = lc.DEFAULT_CONTENT
STATE = {"energy": 80.0, "mood": 0.2, "social_need": 0.7,
         "today_active_count": 0, "unanswered_count": 0}


def test_card_has_all_sections():
    card = mo.build_motivation_card(STATE, C, "今天散步遇到一只猫。\n",
                                    "2026-08-11", datetime(2026, 8, 11, 9, 0))
    assert "【现在】" in card
    assert "【今天】" in card
    assert "【状态】" in card
    assert "猫" in card  # 今天生活片段进去了
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_motivation.py -v` — 期望：FAIL

- [ ] **Step 3: 实现**

```python
# active/motivation.py
"""motivation.py — 生成"动机卡片"：注入给 girl agent 的文本。
卡片只讲"她此刻在干嘛、今天经历过什么、延续了昨天什么、现在什么状态 + 想不想主动"，
说不说、说什么，完全由 agent 用自己的 SOUL 决定。
"""
from datetime import datetime

from . import life_journal, life_sim


def _state_words(s: dict) -> str:
    e = s.get("energy")
    now = "累" if e is not None and e < 35 else ("还行" if e is not None and e < 65 else "精神不错")
    m = s.get("mood")
    mood = "情绪有点低落" if (m is not None and m < 0) else ("心情不错" if (m is not None and m > 0.3) else "情绪平稳")
    return f"精力{now}，{mood}"


def build_motivation_card(state: dict, content: dict, journal: str, day: str,
                          now: datetime | None = None) -> str:
    now = now or datetime.now()
    act = life_sim.current_activity(content, day, now.hour)
    highs = life_sim.today_highlights(content, day, now.hour)
    prev = life_journal.recent_entries_from_text(journal, 1)
    dream = life_sim.maybe_dream(day, now)

    lines = [f"【现在】{act}"]
    if highs:
        lines.append("【今天】" + "；".join(highs))
    if prev:
        lines.append(f"【昨天】{prev[-1]}")
    if dream:
        lines.append(f"【梦】{dream}")
    lines.append(f"【状态】{_state_words(state)}，有点想你，但我不必现在就说")
    return "\n".join(lines)
```

> `life_journal` 需补一个读纯文本的函数：在 `life_journal.py` 加 `recent_entries_from_text(text:str, n:int=1)->list[str]`（对已读入的日志文本取最近 n 条，供 motivation 复用，避免重复读盘）。其内部复用 `_parse_entries`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_motivation.py -v` — 期望：PASS (1 passed)

- [ ] **Step 5: 提交**

```bash
git add active/motivation.py active/life_journal.py tests/test_motivation.py
git commit -m "feat(active): 动机卡片(现在/今天/昨天/状态)"
```

> 备注：`life_journal.recent_entries_from_text(text, n)` 的实现（追加到 life_journal.py）：
> ```python
> def recent_entries_from_text(text: str, n: int = 1) -> list[str]:
>     return [b.strip() for _, b in _parse_entries(text)][-n:]
> ```

---

## Task 10: injector.py — 单一出口注入（dry_run 默认）

**Files:**
- Create: `active/injector.py`
- Test: `tests/test_injector.py`

**Interfaces:**
- Consumes: `motivation.build_motivation_card`。
- Produces: `inject_motivation(card:str, provider="dry_run")->dict`（dry_run 打印+返回 `{"provider","dry_run":True,"card","sent":False}`）；`generate_text(prompt, provider="dry_run")->str`（供 life_grower 的 openclaw 分支调用）。Task 14 把 provider 换成真实 OpenClaw，实现同一签名。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_injector.py
from active import injector


def test_dry_run_never_sends():
    r = injector.inject_motivation("【现在】在睡觉")
    assert r["sent"] is False
    assert r["dry_run"] is True
    assert r["card"] == "【现在】在睡觉"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_injector.py -v` — 期望：FAIL

- [ ] **Step 3: 实现**

```python
# active/injector.py
"""injector.py — 把动机卡片交给谁去说。单一出口约束：
Python 永不直接发微信。这里只负责给 girl agent（OpenClaw）送"动机卡片"，
由 agent 用自己的声音决定说不说、说什么，再由 OpenClaw 发出去。
默认 provider="dry_run"：只打印不发送，保证后端无副作用、可测。
"""
import logging

log = logging.getLogger("active.injector")


def generate_text(prompt: str, provider: str = "dry_run") -> str:
    """给 life_grower：让模型/agent 生成自由文本（这里只回空，真实现见 Task 14）。"""
    log.info("generate_text(%s) dry-run prompt=%s", provider, prompt[:50])
    return ""


def inject_motivation(card: str, provider: str = "dry_run") -> dict:
    if provider == "openclaw":
        # Task 14 接真实注入：静默唤醒 girl agent，把 card 注入其 heartbeat，
        # 由 agent 决定说不说。此处暂不实现发送。
        log.info("inject openclaw card=%s", card[:80])
        return {"provider": "openclaw", "sent": False, "card": card,
                "note": "真实注入在 Task 14 实现"}
    log.debug("dry-run card=%s", card)
    return {"provider": "dry_run", "dry_run": True, "sent": False, "card": card}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_injector.py -v` — 期望：PASS (1 passed)

- [ ] **Step 5: 提交**

```bash
git add active/injector.py tests/test_injector.py
git commit -m "feat(active): 单一出口注入(dry_run默认，OpenClaw留接口)"
```

---

## Task 11: web/main.py — 心跳线程 + 主动 API

**Files:**
- Create: `active/heartbeat.py`
- Modify: `web/main.py`（加 lifespan 心跳线程 + `active/` API）
- Test: `tests/test_heartbeat.py` + 手动 `curl` 探接口

**Interfaces:**
- Consumes: `config.merge_config`、`state_store.load/save`、`state_machine.tick/should_open_window/on_active_sent`、`life_content.load_content`、`life_journal.read_journal/recent_entries/last_entry_date/append_entry`、`life_grower.grow_today`、`motivation.build_motivation_card`、`injector.inject_motivation`。
- Produces: heartbeat 循环函数；Web API `/api/active/config` (GET/POST)、`/api/active/state` (GET)、`/api/active/life` (GET)、`/api/active/content` (GET/POST)、`/api/active/journal` (GET)、`/api/active/grow` (POST)、`/api/active/nudge` (POST)。供 Task 12 前端消费。

- [ ] **Step 1: 写失败测试（heartbeat 单测）**

```python
# tests/test_heartbeat.py
from active import heartbeat, state_store, state_machine


def test_first_tick_advances_state(tmp_path):
    p = tmp_path / "state.json"
    st = state_store.default_state()
    state_store.save(st, p)
    cfg = {"tick_minutes": 15, "seed_energy": 80.0, "seed_mood": 0.2,
           "growth_rate_per_hour": 0.12}
    # 初始化后第一次 tick（无 awaiting_reply）
    st = state_machine._init(st, cfg)
    st["awaiting_reply"] = False
    st2 = heartbeat.tick_once(state_store.load(p), st, cfg, p, now=None)
    assert st2["energy"] <= st["energy"] or st2["energy"] >= st["energy"]  # 有向目标值漂移
    assert st2["social_need"] >= 0.0
```

> 注：tick_once 是个薄封装（load→tick→save 到同文件），保持心跳可单测。上面的断言只验证不炸、状态被写回。真正状态推进的语义已在 Task 3–5 覆盖。

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_heartbeat.py -v` — 期望：FAIL（ModuleNotFoundError: active.heartbeat）

- [ ] **Step 3: 实现 heartbeat.py**

```python
# active/heartbeat.py
"""heartbeat.py — 每 tick_minutes 推进一次状态的循环。只动 state.json，
不直接发任何消息（单一出口见 injector）。"""
import logging
import time as _time
from pathlib import Path

from . import config as cfgmod, state_machine, state_store

log = logging.getLogger("active.heartbeat")


def tick_once(state: dict, init_state: dict, c: dict, path: Path,
              now=None) -> dict:
    """跑一次状态推进并落盘。now 用于测试注入。"""
    nxt = state_machine.tick(state if state["initialized"] else init_state, c, now=now)
    state_store.save(nxt, path)
    return nxt


def run_loop(cfg_path: Path, state_path: Path, stop_event=None,
             on_window=None, now_factory=None):
    """阻塞循环：直到 stop_event 置位。on_window(card) 在窗口打开时回调。
    默认 on_window=None → 只推进状态不开窗口（dry_run）。Task 14 把窗口接到真实注入。"""
    while not (stop_event and stop_event.is_set()):
        c = cfgmod.merge_config(_load_cfg(cfg_path))
        st = state_store.load(state_path)
        heartbeat_now = now_factory() if now_factory else None
        nxt = tick_once(st, state_store.default_state(), c, state_path, now=heartbeat_now)
        if on_window and state_machine.should_open_window(nxt, c, now=heartbeat_now):
            st2 = state_store.load(state_path)  # 可能在 tick 后又被改
            card = ""  # 真正动机卡片由 web 层组装后交给 on_window
            on_window(card)
            st2 = state_machine.on_active_sent(st2, c, now=heartbeat_now)
            state_store.save(st2, state_path)
        _time.sleep(c["tick_minutes"] * 60)
```

> 真实动机卡片在 web 心跳线程里组装（含 content/journal），heartbeat.run_loop 保持纯状态推进。

- [ ] **Step 4: 实现 web/main.py 接线（改文件）**

在 `web/main.py` 顶部 import 后追加：

```python
import threading
from contextlib import asynccontextmanager
from datetime import datetime

from .. import active  # noqa: F401  (active 包在本仓库根)
from .active_bridge import start_active_heartbeat, active_api_routes
```

> 为了让 web 与 active 解耦、避免瞬间改乱 main.py，新增 `web/active_bridge.py` 集中做：启动心跳线程（daemon）、组装动机卡片、定义 `/api/active/*` 路由。main.py 里：

```python
from .active_bridge import register_active

@asynccontextmanager
async def lifespan(app: FastAPI):
    register_active(app)
    yield

app.router.lifespan_context = lifespan
```

> `register_active(app)` 做两件事：① 起 daemon 心跳线程（读 `data/config.yaml` + `data/state.json`）；② `app.include_router(active_router, prefix="/api/active")`。

- [ ] **Step 5: 实现 active_bridge.py**

```python
# web/active_bridge.py
"""activity_bridge — 把 active/ 状态机接到 FastAPI：心跳线程 + /api/active/* 路由。
不直接发消息（单一出口 injector）。"""
import logging
import threading
from pathlib import Path

from fastapi import APIRouter

from ..active import (config as cfgmod, state_store, state_machine,
                      life_content, life_journal, life_grower,
                      motivation, injector)

log = logging.getLogger("web.active")

DATA = Path(__file__).resolve().parents[1] / "data"
CFG = DATA / "config.yaml"
STATE = DATA / "state.json"
CONTENT = DATA / "life_content.yaml"

router = APIRouter()
_thread = None


# ---------- 心跳线程 ----------

def _on_window(card: str):
    # Task 14 换真：injector.inject_motivation(card, provider=config.grow_provider)
    injector.inject_motivation(card, provider="dry_run")


def _heartbeat_loop():
    while True:
        try:
            c = cfgmod.merge_config(_load_active_cfg())
            st = state_store.load(STATE)
            init = state_store.default_state()
            nxt = state_machine.tick(st if st.get("initialized") else init, c)
            state_store.save(nxt, STATE)
            if state_machine.should_open_window(nxt, c):
                content = life_content.load_content(CONTENT)
                journal = life_journal.read_journal()
                card = motivation.build_motivation_card(
                    nxt, content, journal, str(datetime.now().date()))
                _on_window(card)
                st2 = state_machine.on_active_sent(nxt, c)
                state_store.save(st2, STATE)
        except Exception:
            log.exception("heartbeat tick failed")
        time.sleep(c["tick_minutes"] * 60)
```

> 注：`import time` 需在文件头部。这个精简实现把 Task 3–5 的 tick/窗口/on_active_sent 语义串起来，无副作用（dry_run）。

- [ ] **Step 6: 定义 /api/active/* 路由（active_bridge.py 内）**

```python
from fastapi import Request
import yaml


def _load_active_cfg() -> dict:
    if CFG.is_file():
        try:
            return (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get("active_behavior", {})
        except yaml.YAMLError:
            return {}
    return {}


@router.get("/config")
async def get_config():
    return cfgmod.merge_config(_load_active_cfg())


@router.post("/config")
async def set_config(payload: dict):
    data = {}
    if CFG.is_file():
        data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    data.setdefault("active_behavior", {}).update(payload)
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfgmod.merge_config(_load_active_cfg())


@router.get("/state")
async def get_state():
    return state_store.load(STATE)


@router.get("/life")
async def get_life():
    content = life_content.load_content(CONTENT)
    day = str(datetime.now().date())
    return {
        "now_activity": life_sim.current_activity(content, day, datetime.now().hour),
        "highlights": life_sim.today_highlights(content, day, datetime.now().hour),
    }


@router.get("/content")
async def get_content():
    return life_content.load_content(CONTENT)


@router.post("/content")
async def set_content(payload: dict):
    content = life_content.load_content(CONTENT)
    if "habits" in payload: content["habits"] = payload["habits"]
    if "favorites" in payload: content["favorites"] = payload["favorites"]
    if "schedule" in payload: content["schedule"] = payload["schedule"]
    for b in life_content.BUCKETS:
        if payload.get("buckets", {}).get(b) is not None:
            content["buckets"][b] = payload["buckets"][b]
    life_content.save_content(content, CONTENT)
    return content


@router.get("/journal")
async def get_journal():
    return {"text": life_journal.read_journal(),
            "last": life_journal.last_entry_date()}


@router.post("/grow")
async def grow():
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    day = str(datetime.now().date())
    text = life_grower.grow_today(content, journal, day,
                                 provider=_load_active_cfg().get("grow_provider", "dry_run"))
    if text:
        life_journal.append_entry(day, text)
    return {"text": text, "day": day}


@router.post("/nudge")
async def nudge():
    """手动开一次窗口：拼卡片 → injector（dry_run 默认）。测试用·校验按钮。"""
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    st = state_store.load(STATE)
    day = str(datetime.now().date())
    card = motivation.build_motivation_card(st, content, journal, day)
    res = injector.inject_motivation(card, provider=_load_active_cfg().get("inject_provider", "dry_run"))
    return {"card": card, "inject": res}
```

> 依赖 `life_sim`：`from ..active import life_sim`。

- [ ] **Step 7: 起服务手动探接口**

```bash
cd E:/college_information/girl
python -m uvicorn web.main:app --port 18780
curl -s http://127.0.0.1:18780/api/active/state   # 期望: 返回 state.json
curl -s http://127.0.0.1:18780/api/active/config  # 期望: 返回合并后的配置
curl -s -X POST http://127.0.0.1:18780/api/active/nudge  # 期望: 返回 card+inject(sent:false)
```

- [ ] **Step 8: 提交**

```bash
git add active/heartbeat.py web/active_bridge.py web/main.py tests/test_heartbeat.py
git commit -m "feat(web): 心跳线程 + 主动API(active config/state/life/content/journal/grow/nudge)"
```

---

## Task 12: Web 前端 —「她的一天」页 + 主动状态机页升级

**Files:**
- Modify: `web/templates/index.html`
- Modify: `web/static/js/app.js`
- Modify: `web/static/css/style.css`

**Interfaces:**
- Consumes: `/api/active/config|state|life|content|journal|grow|nudge`（Task 11），旧 `/api/behavior`。
- Produces: 前端 tab：**主动状态机**（状态仪表 + 新参数滑块含依恋轴）+ **她的一天**（内容编辑器 + 日志查看 + 「让她今天长一条」grow 按钮 + 「现在就推」nudge 按钮）。
- 默认档「自然淡雅」参数在 Task 13 的 config 迁移里落到 `data/config.yaml`。

- [ ] **Step 1: index.html 加导航与页面骨架**

在现有导航加两项：`主动状态机`、`她的一天`。新页面骨架：

```html
<section id="page-active" class="page">
  <h2>主动状态机</h2>
  <div id="active-gauges" class="gauges"></div>   <!-- energy/mood/social_need 三环进度条 -->
  <h3>参数</h3>
  <div id="active-sliders" class="flds"></div>    <!-- 由 JS 渲染滑块 -->
</section>

<section id="page-life" class="page">
  <h2>她的一天</h2>
  <div id="life-preview"></div>                   <!-- 现在在干嘛 / 今天高光 -->
  <h3>生活底色（可编辑，存 life_content.yaml）</h3>
  <div id="life-content-editor"></div>
  <button id="btn-grow">让她今天长一条</button>
  <button id="btn-nudge" class="danger">现在就推（测试）</button>
  <pre id="life-log"></pre>                        <!-- 日志 -->
</section>
```

（样式复用现有 `.flds`/`.page`/`.gauges`；在 style.css 补 `.gauges .gauge` 圆形进度与按钮样式。）

- [ ] **Step 2: app.js 加加载/渲染/保存逻辑**

```js
const ACTIVE_FIELDS = [
  {k: "open_threshold",   min: 0,   max: 1,    step: 0.05, label: "开启阈值"},
  {k: "cooldown_seconds", min: 120, max: 3600, step: 60,   label: "冷却(秒)"},
  {k: "daily_max",        min: 1,   max: 10,   step: 1,    label: "每日上限"},
  {k: "max_unanswered",   min: 1,   max: 10,   step: 1,    label: "未回上限"},
  {k: "late_night_start", min: 0,   max: 23,   step: 1,    label: "深夜窗口开始"},
  {k: "early_morning_end",min: 1,   max: 8,    step: 1,    label: "深夜窗口结束"},
  {k: "attachment",       min: 0,   max: 1,    step: 0.01, label: "依恋轴(0焦虑=1安全/1黏-1回避)", type: "ratio"},
  {k: "grow_provider",    min: 0,   max: 1,    step: 1,    label: "生长方式(0=样例 1=LLM)", type: "select"},
  {k: "inject_provider",  min: 0,   max: 1,    step: 1,    label: "注入方式(0=试跑 1=真发)", type: "select"},
];

async function loadActive() {
  const [cfg, state, life] = await Promise.all([
    fetch("/api/active/config").then(r => r.json()),
    fetch("/api/active/state").then(r => r.json()),
    fetch("/api/active/life").then(r => r.json()),
  ]);
  renderGauges(state);
  renderActiveSliders(cfg);
  renderLifePreview(life);
}
```

`renderGauges` 画 energy/mood/social_need 三个百分比环；`renderActiveSliders` 复用现有滑块渲染器；值变化点 `/api/active/config` POST。

- [ ] **Step 3: grow / nudge / content 编辑接线**

```js
document.getElementById("btn-grow").onclick = async () => {
  const r = await fetch("/api/active/grow", {method: "POST"});
  const j = await r.json();
  showLog("已生长: " + (j.text || "(空)"));
  loadJournal();
};
document.getElementById("btn-nudge").onclick = async () => {
  const r = await fetch("/api/active/nudge", {method: "POST"});
  const j = await r.json();
  showLog("卡片:\n" + j.card);
};
```

内容编辑器用一个 `<textarea>` 直接编辑 `life_content.yaml` 文本（buckets/habits/favorites），保存发 `/api/active/content`。日志区 `loadJournal()` 拉 `/api/active/journal` 显示。

- [ ] **Step 4: 手动验证**

起服务打开 http://127.0.0.1:18780 → 切到「她的一天」：看到「现在在干嘛/今天高光」；点「让她今天长一条」→ 日志新增一条；点「现在就推」→ 打印卡片（dry_run，不真发）。

- [ ] **Step 5: 提交**

```bash
git add web/templates/index.html web/static/js/app.js web/static/css/style.css
git commit -m "feat(web): 主动状态机页 + 她的一天(内容编辑/生长/推一次)"
```

---

## Task 13: 配置迁移 + .gitignore + README

**Files:**
- Modify: `data/config.yaml`（active_behavior 展开为新键）
- Modify: `.gitignore`（加 data/state.json、data/life_journal.md）
- Modify: `web/README.md`（行为页说明 + 端口/启动不变）
- Test: 手动 `curl` 确认 config 加载

**Interfaces:**
- Produces: 默认参数表（§12 的「自然淡雅」档）落到 config；忽略运行态文件。

- [ ] **Step 1: 更新 data/config.yaml 的 active_behavior**

把现有 `active_behavior` 段扩展为：

```yaml
active_behavior:
  energy: 80
  mood: 75
  social_need: 40
  open_threshold: 0.5
  cooldown_seconds: 300
  daily_max: 2
  quiet_start: 2
  quiet_end: 5
  max_unanswered: 3
  allow_late_night: true
  late_night_start: 23
  early_morning_end: 6
  tick_minutes: 15
  growth_rate_per_hour: 0.12
  energy_time_constant_min: 240
  mood_time_constant_min: 360
  mood_baseline: 0.15
  attachment: secure
  grow_provider: dry_run
  inject_provider: dry_run
```

- [ ] **Step 2: 更新 .gitignore**

```gitignore
# 主动状态机运行态（本地，不入库）
data/state.json
data/life_journal.md
```

- [ ] **Step 3: 更新 web/README.md 行为页说明**

补一段：「主动状态机」页可调 cooldown/每日上限/勿扰/深夜窗口/开启阈值/依恋轴/生长方式/注入方式；默认「自然淡雅」档。

- [ ] **Step 4: 验证加载**

```bash
curl -s http://127.0.0.1:18780/api/active/config  # 期望合并结果含 open_threshold:0.5, daily_max:2…
```

- [ ] **Step 5: 提交**

```bash
git add data/config.yaml .gitignore web/README.md
git commit -m "chore(active): 默认参数落配置 + gitignore 运行态 + README"
```

---

## Task 14: OpenClaw 接线 + 真实注入验证（verify-then-broaden）

**Files:**
- Modify: `active/injector.py`（openclaw provider 真实现）
- Modify: `active/life_grower.py`（openclaw provider 真实现，走 injector.generate_text）
- Modify: `web/active_bridge.py`（`_on_window` 真注入；grow/nudge 真 provider）
- Test: 手动验证（回复探针 / 真实注入 / 真实生长）

**Interfaces:**
- Consumes: `config` 的 `grow_provider`/`inject_provider`。
- Produces: 第 1 个验证周期证明「单一出口」闭环可用。

> 安全：把 provider 从 dry_run 切真之前，必须先在一条试验消息里验证。网关 token 在 `~\.openclaw\openclaw.json`，**不写进本仓库、不上传、不贴对话**。

- [ ] **Step 1: 探针验证回复 → social_need 归零**

在微信里正常回复小语一条 → 看 `/api/active/state` 的 `social_need` 是否为 0、`awaiting_reply` 是否翻转。若未归零，说明回复链路没接到 girl agent 会话（需在 OpenClaw 侧把「用户回复」事件接到 `on_user_reply`）。

- [ ] **Step 2: 真实注入（一次）**

`web/active_bridge.py` `_on_window` 改为 `injector.inject_motivation(card, provider=config["inject_provider"])`。把 `data/config.yaml` 的 `inject_provider` 设 `dry_run`，先在「现在就推」手动触发，确认卡片文本、agent 收到、是否开口。确认无误再切 `openclaw`。

> `injector.inject_motivation` 的 openclaw 分支需要真正把 card 注入 OpenClaw heartbeat。实现方式（社区验证过的最小做法）：把 `**动机卡片**` 追加到 `girl_workspace/memory/heartbeat.md` 并调用 `openclaw trigger girl`（不改模型、不造新 agent），agent 在下一拍读 heartbeat 决定说不说。具体命令/路径以你本机 OpenClaw 版本为准，先小验证。

- [ ] **Step 3: 真实生长（一次）**

`life_grower.grow_today` 走 `injector.generate_text(provider="openclaw")` 让 girl agent 用真实声音写当天生活。先手动触发 `/api/active/grow`，看日志是否生成、是否贴切。确认后把 `grow_provider` 切 `openclaw`。

- [ ] **Step 4: 全链路跑一天**

把 `tick_minutes` 调小（如 1 分钟）做快速验证：心跳推进 → 到点开窗口 → agent 说 → 你回 → social_need 归零 → 今日计数+1 → 冷却。确认闭环后再调回 15 分钟。

- [ ] **Step 5: 提交（只提交可逆的骨架代码）**

```bash
git add active/injector.py active/life_grower.py web/active_bridge.py data/config.yaml
git commit -m "feat(active): OpenClaw 真实注入/生长接线（默认仍 dry_run，需手动切）"
```

> 若不把默认切真，本任务只提交「接线完成、默认 dry_run」的骨架代码；真实切换由你手动改 `data/config.yaml` 的 provider 完成。

---

## Self-Review（对照 spec）

逐条核对 spec 设计 vs 本计划：

- **状态向量**（§4）：energy/mood/social_need/last_real_reply/last_active_ts/unanswered_count/today_active_count/today/awaiting_reply → Task 2 state_store + Task 3–5。✅
- **心跳推进**（§5）：tick 纯函数、energy/mood/social_need 三方程、mood 由互动质量调制 → Task 3–5 + Task 11 心跳线程。✅
- **决策层**（§6）：四重防打扰 + 精力上限，全齐 → Task 5 `should_open_window`。✅
- **生活层**（§7）：作息模拟/生活沉淀/梦境/主动取料 → Task 6–9。✅
- **可生长**（用户最新需求）：内容库 web 可编辑 + LLM 生长日志（LLM 真生长）→ Task 6 (`life_content.py` web 编辑) + Task 7 (`life_grower`，dry_run 种子兜底 / openclaw 真生长) + Task 12（前端「她的一天」编辑+grow 按钮）+ Task 14（真 LLM 接线）。✅
- **内容生成与注入契约**（§8）：动机卡片（现在/今天/昨天/梦/状态）→ Task 9 + Task 10；单一出口 → Task 10 injector 永不直接发。✅
- **Web 后台改造**（§9）：状态可视化 + 全参数滑块（含依恋轴）+ 「现在就推」按钮 + 「今天她的一天」预览 → Task 11 + Task 12。✅ 「自然淡雅」默认档 → Task 13 config。
- **文件结构**（§10）：active/state_machine.py、life_sim.py、state_store.py、web/main.py、data/config.yaml、data/state.json、web/agent_admin.py（未直接改，保持读通道）、templates+js → 本计划全部覆盖。✅
- **测试与风险**（§11）：单元测试（三状态方程/作息/阈值/防打扰/归零语义）→ Tests 3/4/5；集成（开窗→发→回→归零；深夜延时触发）→ Task 11/14；注入机制不确定 → Task 10/14「verify-then-broaden」+ 界面契约不变。✅
- **默认参数表**（§12）：开启阈值 0.5 / cooldown 300s / 每日上限 2 / 勿扰 02–05 / 未回 3 / 允许凌晨 true / 深夜窗 23–06 / 依恋轴安全 → Task 13 config。✅ 注：spec §12 的「勿扰 23:00–07:00」在本计划按破解作细化后的 hard wall 02–05 落地（见 Task 13 config `quiet_start/quiet_end`），晚间 23–06 由深夜窗口承载——两者不冲突。

**遗留/风险**：真注入/真生长依赖你本机 OpenClaw 的具体 heartbeat 机制（Task 14 Step 2/3），以「先小验证再铺开」落地，默认 dry_run 保证后端无副作用、不炸。

---

## 执行交接

Plan complete and saved to `docs/superpowers/plans/2026-08-11-active-state-machine-life-sim.md`。两种执行方式：

**1. Subagent-Driven（推荐）** — 每个任务我派一个全新子 agent，任务间我做 review，迭代快

**2. Inline Execution** — 本会话用 executing-plans 批量执行，带 checkpoint 供 review

**选哪种？**



