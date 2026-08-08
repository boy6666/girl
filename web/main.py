"""
web/main.py — 小语的 Web 伴侣后台（FastAPI）

职责（VISION 的 web/ 部分）：
- 人格滑块页：5 维滑块 → 渲染重写 SOUL.md → 下条消息生效
- 记忆可视化：读 OpenClaw girl agent 会话
- 状态页：模型 / 网关 / 路由信息
- 行为配置：读写主动行为参数（V1 cron 的基础，V1.5 状态机预留）

约束：不直接发微信（单一出口 OpenClaw/ClawBot）。API key 不在此，潜伏于 OpenClaw 配置。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import agent_admin, soul_render

BASE = Path(__file__).resolve().parent
PERSONALITY_YAML = BASE / "personality.yaml"
BEHAVIOR_YAML = BASE.parent / "data" / "config.yaml"

app = FastAPI(title="小语 · 伴侣后台", version="0.1.0")

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


# ============ 人格滑块持久化 ============

def _load_personality() -> dict:
    if PERSONALITY_YAML.is_file():
        try:
            data = yaml.safe_load(PERSONALITY_YAML.read_text(encoding="utf-8")) or {}
            return soul_render.validate(data.get("personality", {}))
        except yaml.YAMLError:
            pass
    return dict(soul_render.DEFAULT_VALUES)


def _save_personality(values: dict) -> dict:
    vals = soul_render.validate(values)
    obj = {"personality": vals}
    PERSONALITY_YAML.write_text(
        yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return vals


# ============ 行为参数持久化（V1 基础 / V1.5 预留） ============

def _load_behavior() -> dict:
    if BEHAVIOR_YAML.is_file():
        try:
            data = yaml.safe_load(BEHAVIOR_YAML.read_text(encoding="utf-8")) or {}
            return data.get("active_behavior", {})
        except yaml.YAMLError:
            pass
    return {}


def _save_behavior(updates: dict) -> dict:
    if not BEHAVIOR_YAML.is_file():
        # 没有则用默认骨架初始化
        base = {"active_behavior": {}}
        BEHAVIOR_YAML.write_text(
            yaml.safe_dump(base, allow_unicode=True, sort_keys=False), encoding="utf-8")
        data = base
    else:
        data = yaml.safe_load(BEHAVIOR_YAML.read_text(encoding="utf-8")) or {}
    data.setdefault("active_behavior", {}).update(updates)
    BEHAVIOR_YAML.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return data["active_behavior"]


# ============ 页面 ============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


# ============ 人格滑块 API ============

@app.get("/api/personality")
async def get_personality():
    return _load_personality()


@app.post("/api/personality")
async def set_personality(payload: dict):
    values = _load_personality()
    for k in soul_render.DIMENSIONS:
        if k in payload:
            values[k] = payload[k]
    lowered = _save_personality(values)
    # 渲染滑块段并写回 SOUL.md（下条消息生效）
    section = soul_render.render_slider_section(lowered)
    applied = agent_admin.apply_personality(section)
    return {
        "success": True,
        "personality": lowered,
        "soul_changed": applied["changed"],
        "preview": applied["soul"],
        "note": "已写入 SOUL.md，下一条消息生效" if applied["changed"] else "数值相同，未改动",
    }


# ============ 人格文件查看 ============

@app.get("/api/soul")
async def get_soul():
    return {"content": agent_admin.read_file("SOUL.md")}


@app.get("/api/agent/files")
async def get_agent_files():
    files = []
    for name in agent_admin.WORKSPACE_FILES:
        files.append({"name": name, "content": agent_admin.read_file(name)})
    return {"files": files}


# ============ 记忆可视化 ============

@app.get("/api/memory")
async def get_memory():
    sessions = agent_admin.list_sessions()
    total = sum(len(s.get("messages", [])) for s in sessions)
    return {"sessions": sessions, "total_messages": total}


# ============ 状态 ============

@app.get("/api/status")
async def get_status():
    return {
        "model": "deepseek/deepseek-v4-flash",
        "agents": ["main", "girl"],
        "girl_agent": {
            "workspace": str(agent_admin.WORKSPACE),
            "sessions": len(agent_admin.list_sessions()),
            "messages": agent_admin.count_messages(),
        },
        "channel": "openclaw-weixin",
        "note": "网关/模型健康请用 `openclaw status` 查看",
    }


# ============ 行为配置 ============

@app.get("/api/behavior")
async def get_behavior():
    return _load_behavior()


@app.post("/api/behavior")
async def set_behavior(payload: dict):
    saved = _save_behavior(payload)
    return {"success": True, "behavior": saved}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.main:app", host="127.0.0.1", port=8000, reload=True)
