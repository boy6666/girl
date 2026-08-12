"""heartbeat.py — 每 tick_minutes 推进一次状态的循环。只动 state.json，
不直接发任何消息（单一出口见 injector）。"""
import logging
import time as _time
from pathlib import Path

from . import config as cfgmod, state_machine, state_store

log = logging.getLogger("active.heartbeat")


def tick_once(state: dict, init_state: dict, c: dict, path: Path,
              now=None) -> dict:
    """跑一次状态推进并落盘到 path。now 用于测试注入。"""
    c = cfgmod.merge_config(c)
    nxt = state_machine.tick(state if state.get("initialized") else init_state,
                             c, now=now)
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
        nxt = tick_once(st, state_store.default_state(), c, state_path,
                        now=heartbeat_now)
        if on_window and state_machine.should_open_window(nxt, c, now=heartbeat_now):
            st2 = state_store.load(state_path)  # tick 后可能又被改
            card = ""  # 真实动机卡片由 web 层组装后交给 on_window
            on_window(card)
            st2 = state_machine.on_active_sent(st2, c, now=heartbeat_now)
            state_store.save(st2, state_path)
        _time.sleep(c["tick_minutes"] * 60)


def _load_cfg(cfg_path: Path) -> dict:
    try:
        import yaml
        if cfg_path.is_file():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            return data.get("active_behavior", {})
    except Exception:  # noqa: BLE001 — 配置坏了也要能跑（回默认）
        log.exception("load cfg failed: %s", cfg_path)
    return {}
