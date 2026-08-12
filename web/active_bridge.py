"""web/active_bridge.py — 把 active/ 状态机接到 FastAPI：心跳线程 + /api/active/* 路由。
不直接发消息（单一出口见 injector）。dry_run 默认，Task 14 换真 provider。"""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from active import (config as cfgmod, state_store, state_machine,
                    life_content, life_journal, life_grower, life_sim,
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
    # 自动窗口也读 inject_provider（与 /nudge 一致）：dry_run 只打印；
    # openclaw 把卡片写进心跳文件由小语决定说不说。默认 dry_run，可回滚。
    return injector.inject_motivation(
        card, provider=_active_cfg().get("inject_provider", "dry_run"))


def _heartbeat_loop():
    while True:
        try:
            c = _active_cfg()
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
        except Exception:            # noqa: BLE001 — 心跳绝不被异常打断
            log.exception("heartbeat tick failed")
        time.sleep(c["tick_minutes"] * 60)


def start_active_heartbeat():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_heartbeat_loop, name="active-heartbeat",
                               daemon=True)
    _thread.start()


# ---------- 配置读 ----------

def _active_cfg() -> dict:
    c = {}
    if CFG.is_file():
        try:
            c = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "active_behavior", {})
        except yaml.YAMLError:
            c = {}
    return cfgmod.merge_config(c)


def register_active(app):
    """① 起 daemon 心跳线程；② 挂 /api/active/* 路由。"""
    start_active_heartbeat()
    app.include_router(router, prefix="/api/active")


# ---------- 路由 ----------

@router.get("/config")
async def get_config():
    return _active_cfg()


@router.post("/config")
async def set_config(payload: dict):
    data = {}
    if CFG.is_file():
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
    data.setdefault("active_behavior", {}).update(payload)
    CFG.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    return _active_cfg()


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
    # 前端文本编辑器直接发整份 life_content（JSON/YAML）文本
    if "yaml" in payload:
        try:
            text = yaml.safe_load(payload["yaml"])
        except yaml.YAMLError as e:
            return JSONResponse({"error": f"YAML 解析失败: {e}"}, status_code=400)
        if isinstance(text, dict):
            life_content.save_content(text, CONTENT)
            return life_content.load_content(CONTENT)
        return JSONResponse({"error": "内容必须是一个对象"}, status_code=400)
    # 结构化合并（Task 11 行为）
    content = life_content.load_content(CONTENT)
    if "habits" in payload:
        content["habits"] = payload["habits"]
    if "favorites" in payload:
        content["favorites"] = payload["favorites"]
    if "schedule" in payload:
        content["schedule"] = payload["schedule"]
    for b in life_content.BUCKETS:
        if payload.get("buckets", {}).get(b) is not None:
            content["buckets"][b] = payload["buckets"][b][:25]
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
                                  provider=_active_cfg().get("grow_provider", "dry_run"))
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
    res = injector.inject_motivation(
        card, provider=_active_cfg().get("inject_provider", "dry_run"))
    return {"card": card, "inject": res}
