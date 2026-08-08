"""
AI Girlfriend Bot - 主入口文件
"""
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import config
from app.database import db
from app.vector_db import vector_db
from app.chat import chat_engine
from app.behavior import behavior_engine
from app.sticker import sticker_system


# ============ 初始化 ============

# 确保数据目录存在
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============ Web 应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 启动 AI Girlfriend Bot...")

    # 启动主动行为引擎
    def send_message(msg):
        # 发送主动消息（需要先连接微信）
        print(f"[主动消息] {msg}")

    behavior_engine.set_message_callback(send_message)
    await behavior_engine.start()

    yield

    # 关闭
    print("👋 关闭 AI Girlfriend Bot...")
    await behavior_engine.stop()


app = FastAPI(
    title="AI Girlfriend Bot",
    description="一个高度人格化的AI女友机器人",
    version="1.0.0",
    lifespan=lifespan
)

# 静态文件和模板
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ============ API 路由 ============

@app.get("/", response_class=HTMLResponse)
async def home():
    """主页"""
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/api/config/personality")
async def get_personality():
    """获取人格配置"""
    return config.config.personality.model_dump()


@app.post("/api/config/personality")
async def update_personality(updates: dict):
    """更新人格配置"""
    config.update("personality", updates)
    return {"success": True, "personality": config.config.personality.model_dump()}


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    behavior_status = behavior_engine.get_status()
    return {
        "behavior": behavior_status,
        "memory_facts": len(db.get_facts()),
        "memory_vectors": vector_db.count(),
        "sticker_stats": sticker_system.get_stats(),
        "connected": True  # TODO: 检查微信连接状态
    }


@app.get("/api/memory/facts")
async def get_memory_facts(limit: int = 50):
    """获取记忆事实列表"""
    facts = db.get_facts(limit=limit)
    return [
        {
            "id": f.id,
            "subject": f.subject,
            "predicate": f.predicate,
            "object": f.object,
            "created_at": f.created_at.isoformat() if f.created_at else None
        }
        for f in facts
    ]


@app.delete("/api/memory/facts/{fact_id}")
async def delete_memory_fact(fact_id: int):
    """删除记忆事实"""
    success = db.delete_fact(fact_id)
    return {"success": success}


@app.get("/api/conversations")
async def get_conversations(limit: int = 20):
    """获取对话历史"""
    convs = db.get_recent_conversations(limit=limit)
    return [
        {
            "id": c.id,
            "user_message": c.user_message,
            "ai_response": c.ai_response,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "emotion_tag": c.emotion_tag
        }
        for c in convs
    ]


@app.post("/api/chat")
async def test_chat(message: dict):
    """测试聊天接口"""
    user_msg = message.get("message", "")
    if not user_msg:
        return {"error": "消息不能为空"}

    response, emotion = await chat_engine.generate_response(user_msg)
    return {
        "response": response,
        "emotion": emotion,
        "sticker": sticker_system.get_sticker_path(emotion)
    }


@app.post("/api/chat/reset")
async def reset_chat():
    """重置对话历史"""
    chat_engine.reset_history()
    return {"success": True}


# ============ WebSocket 实时更新 ============

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时连接"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接，每5秒发送心跳
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "ping",
                "status": behavior_engine.get_status()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn

    port = config.config.server.port
    print(f"""
╔══════════════════════════════════════════════╗
║       🤖 AI Girlfriend Bot v1.0              ║
╠══════════════════════════════════════════════╣
║  📱 Web 控制台: http://localhost:{port}            ║
║  📡 WebSocket: ws://localhost:{port}/ws          ║
║  📝 API 文档:   http://localhost:{port}/docs      ║
╠══════════════════════════════════════════════╣
║  ⚠️  请确保 ClawBot 已启动                     ║
╚══════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host=config.config.server.host,
        port=port,
        reload=config.config.server.debug
    )