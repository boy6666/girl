"""
AI Girlfriend Bot - 应用包初始化
"""
from app.config import config
from app.database import db
from app.vector_db import vector_db
from app.memory import memory_system
from app.chat import chat_engine
from app.behavior import behavior_engine
from app.wechat import wechat_adapter
from app.sticker import sticker_system

__all__ = [
    'config',
    'db',
    'vector_db',
    'memory_system',
    'chat_engine',
    'behavior_engine',
    'wechat_adapter',
    'sticker_system',
]