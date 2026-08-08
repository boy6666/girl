"""
数据库模块 - SQLite 存储结构化数据
包括：记忆事实、对话历史、人格参数、事件日志
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel


Base = declarative_base()


class MemoryFact(Base):
    """记忆事实表 - 存储提取的三元组"""
    __tablename__ = 'memory_facts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(200), nullable=False)      # 主体
    predicate = Column(String(100), nullable=False)    # 关系
    object = Column(Text, nullable=True)               # 对象（可为长文本）
    confidence = Column(Float, default=1.0)            # 置信度
    source = Column(String(50), default='chat')        # 来源：chat/memory/dream
    emotion_tag = Column(String(50), nullable=True)    # 情绪标签
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)          # 是否有效（软删除）


class ConversationTurn(Base):
    """对话轮次表 - 短期上下文"""
    __tablename__ = 'conversation_turns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    emotion_tag = Column(String(50), nullable=True)    # 回复情绪
    had_image = Column(Boolean, default=False)
    had_voice = Column(Boolean, default=False)


class MemorySummary(Base):
    """记忆摘要表 - 对话摘要，用于向量检索"""
    __tablename__ = 'memory_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    vector_id = Column(String(100), nullable=True)     # Chroma 中的 ID
    timestamp = Column(DateTime, default=datetime.now)
    emotion_tag = Column(String(50), nullable=True)
    importance = Column(Integer, default=5)            # 重要性 1-10


class EventLog(Base):
    """事件日志表 - 主动行为记录"""
    __tablename__ = 'event_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)    # 类型：initiative/sleep/dream/...
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    metadata = Column(JSON, nullable=True)             # 额外数据


class UserProfile(Base):
    """用户画像表"""
    __tablename__ = 'user_profile'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, nullable=False)
    last_active = Column(DateTime, default=datetime.now)
    total_messages = Column(Integer, default=0)
    avg_response_length = Column(Float, default=0)
    preferences = Column(JSON, nullable=True)          # 偏好设置


class Diary(Base):
    """日记表 - V3.0 功能"""
    __tablename__ = 'diaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.now)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)
    mood_score = Column(Integer, nullable=True)        # 当日情绪评分


# ============ Pydantic 模型 ============

class MemoryFactSchema(BaseModel):
    id: Optional[int] = None
    subject: str
    predicate: str
    object: Optional[str] = None
    confidence: float = 1.0
    source: str = 'chat'
    emotion_tag: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    id: Optional[int] = None
    user_message: str
    ai_response: str
    timestamp: Optional[datetime] = None
    emotion_tag: Optional[str] = None

    class Config:
        from_attributes = True


# ============ 数据库管理器 ============

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "sqlite.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,
            connect_args={'check_same_thread': False}
        )
        Base.metadata.create_all(self.engine)

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_session(self) -> Session:
        return self.SessionLocal()

    # ---------- 记忆事实操作 ----------

    def add_fact(self, subject: str, predicate: str, obj: str = None,
                 confidence: float = 1.0, source: str = 'chat',
                 emotion_tag: str = None) -> MemoryFact:
        """添加记忆事实"""
        session = self.get_session()
        try:
            # 检查是否已存在相同事实
            existing = session.query(MemoryFact).filter(
                MemoryFact.subject == subject,
                MemoryFact.predicate == predicate,
                MemoryFact.object == obj,
                MemoryFact.is_active == True
            ).first()

            if existing:
                existing.confidence = min(existing.confidence + 0.1, 1.0)
                existing.updated_at = datetime.now()
                session.commit()
                return existing

            fact = MemoryFact(
                subject=subject,
                predicate=predicate,
                object=obj,
                confidence=confidence,
                source=source,
                emotion_tag=emotion_tag
            )
            session.add(fact)
            session.commit()
            session.refresh(fact)
            return fact
        finally:
            session.close()

    def get_facts(self, subject: str = None, limit: int = 100) -> List[MemoryFact]:
        """获取记忆事实"""
        session = self.get_session()
        try:
            query = session.query(MemoryFact).filter(MemoryFact.is_active == True)
            if subject:
                query = query.filter(MemoryFact.subject == subject)
            return query.order_by(MemoryFact.updated_at.desc()).limit(limit).all()
        finally:
            session.close()

    def delete_fact(self, fact_id: int) -> bool:
        """软删除记忆事实"""
        session = self.get_session()
        try:
            fact = session.query(MemoryFact).filter(MemoryFact.id == fact_id).first()
            if fact:
                fact.is_active = False
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ---------- 对话历史操作 ----------

    def add_conversation(self, user_msg: str, ai_resp: str,
                        emotion_tag: str = None,
                        had_image: bool = False,
                        had_voice: bool = False) -> ConversationTurn:
        """添加对话轮次"""
        session = self.get_session()
        try:
            turn = ConversationTurn(
                user_message=user_msg,
                ai_response=ai_resp,
                emotion_tag=emotion_tag,
                had_image=had_image,
                had_voice=had_voice
            )
            session.add(turn)
            session.commit()
            session.refresh(turn)
            return turn
        finally:
            session.close()

    def get_recent_conversations(self, limit: int = 10) -> List[ConversationTurn]:
        """获取最近的对话"""
        session = self.get_session()
        try:
            return session.query(ConversationTurn)\
                .order_by(ConversationTurn.timestamp.desc())\
                .limit(limit)\
                .all()
        finally:
            session.close()

    # ---------- 记忆摘要操作 ----------

    def add_summary(self, content: str, vector_id: str = None,
                   emotion_tag: str = None, importance: int = 5) -> MemorySummary:
        """添加记忆摘要"""
        session = self.get_session()
        try:
            summary = MemorySummary(
                content=content,
                vector_id=vector_id,
                emotion_tag=emotion_tag,
                importance=importance
            )
            session.add(summary)
            session.commit()
            session.refresh(summary)
            return summary
        finally:
            session.close()

    def get_important_summaries(self, limit: int = 20) -> List[MemorySummary]:
        """获取重要记忆摘要"""
        session = self.get_session()
        try:
            return session.query(MemorySummary)\
                .filter(MemorySummary.importance >= 7)\
                .order_by(MemorySummary.timestamp.desc())\
                .limit(limit)\
                .all()
        finally:
            session.close()

    # ---------- 事件日志操作 ----------

    def log_event(self, event_type: str, content: str,
                  metadata: Dict[str, Any] = None) -> EventLog:
        """记录事件"""
        session = self.get_session()
        try:
            event = EventLog(
                event_type=event_type,
                content=content,
                metadata=metadata
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event
        finally:
            session.close()

    # ---------- 用户画像操作 ----------

    def update_user_profile(self, user_id: str, **kwargs):
        """更新用户画像"""
        session = self.get_session()
        try:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)

            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            session.commit()
            return profile
        finally:
            session.close()


# 全局数据库实例
db = DatabaseManager()