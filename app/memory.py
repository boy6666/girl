"""
记忆系统模块 - 负责记忆的提取、存储、检索
"""
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.config import config
from app.database import db, MemoryFactSchema
from app.vector_db import vector_db


class MemoryExtractor:
    """记忆提取器 - 从对话中提取三元组事实"""

    def __init__(self):
        self.local_api_base = config.config.ai.local_api_base
        self.local_model = config.config.ai.local_model

    async def extract_facts(self, user_message: str, ai_response: str) -> List[Dict]:
        """从对话中提取记忆事实

        Returns:
            三元组列表 [{"subject": "", "predicate": "", "object": ""}]
        """
        prompt = f"""从以下对话中提取关键事实，以JSON数组格式返回。
只提取关于"用户"的事实，如用户的喜好、习惯、事件等。
格式：[{{"subject": "主体", "predicate": "关系", "object": "对象"}}]

对话：
用户：{user_message}
AI：{ai_response}

只返回JSON数组，不要其他内容。如果没找到事实，返回空数组[]。"""

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.local_api_base}/api/generate",
                    json={
                        "model": self.local_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 500}
                    }
                )
                result = response.json()
                text = result.get('response', '')

                # 提取JSON
                json_match = re.search(r'\[.*\]', text, re.DOTALL)
                if json_match:
                    facts = json.loads(json_match.group())
                    return facts
        except Exception as e:
            print(f"记忆提取失败: {e}")

        return []

    async def generate_summary(self, user_message: str, ai_response: str) -> str:
        """生成对话摘要"""
        prompt = f"""用50-200字总结以下对话的核心内容和要点：

用户：{user_message}
AI：{ai_response}

只返回摘要，不要其他内容。"""

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.local_api_base}/api/generate",
                    json={
                        "model": self.local_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 300}
                    }
                )
                result = response.json()
                return result.get('response', '').strip()
        except Exception as e:
            print(f"摘要生成失败: {e}")
            return f"用户说：{user_message[:50]}..."


class MemorySystem:
    """记忆系统 - 管理记忆的存储和检索"""

    def __init__(self):
        self.extractor = MemoryExtractor()
        self.threshold = config.config.memory.similarity_threshold

    async def save_interaction(self, user_message: str, ai_response: str,
                               emotion_tag: str = None) -> None:
        """保存一次交互

        1. 提取三元组存储到 SQLite
        2. 生成摘要存储到 Chroma
        """
        # 提取并保存事实
        facts = await self.extractor.extract_facts(user_message, ai_response)
        for fact in facts:
            db.add_fact(
                subject=fact.get('subject', '用户'),
                predicate=fact.get('predicate', ''),
                obj=fact.get('object', ''),
                confidence=0.8,
                source='chat',
                emotion_tag=emotion_tag
            )

        # 生成并保存摘要
        summary_text = await self.extractor.generate_summary(user_message, ai_response)
        if summary_text:
            summary = db.add_summary(
                content=summary_text,
                emotion_tag=emotion_tag,
                importance=5
            )

            # 存入向量数据库
            try:
                vector_id = vector_db.add_memory(
                    text=summary_text,
                    metadata={
                        'id': f"sum_{summary.id}",
                        'timestamp': datetime.now().isoformat(),
                        'emotion_tag': emotion_tag,
                        'db_id': summary.id
                    }
                )
                # 更新关联
                summary.vector_id = vector_id
            except Exception as e:
                print(f"向量存储失败: {e}")

        # 保存对话历史
        db.add_conversation(
            user_msg=user_message,
            ai_resp=ai_response,
            emotion_tag=emotion_tag
        )

    def retrieve(self, query: str, max_results: int = 5) -> Tuple[List[str], List[Dict]]:
        """检索相关记忆

        Returns:
            (记忆摘要列表, 事实列表)
        """
        # 向量检索
        vector_memories = vector_db.search(
            query=query,
            n_results=max_results,
            threshold=self.threshold
        )
        summaries = [m['content'] for m in vector_memories]

        # 精确事实检索（从 SQLite）
        # 简单关键词匹配
        facts = db.get_facts(limit=max_results * 2)
        relevant_facts = []
        for fact in facts:
            if (query.lower() in fact.object.lower() or
                query.lower() in fact.subject.lower()):
                relevant_facts.append({
                    'subject': fact.subject,
                    'predicate': fact.predicate,
                    'object': fact.object
                })

        return summaries, relevant_facts

    def build_memory_context(self, current_message: str) -> str:
        """构建记忆上下文供 Prompt 使用"""
        summaries, facts = self.retrieve(current_message)

        context_parts = []

        if summaries:
            context_parts.append("【相关记忆摘要】")
            for i, s in enumerate(summaries[:3], 1):
                context_parts.append(f"{i}. {s}")

        if facts:
            context_parts.append("\n【已了解的事实】")
            for f in facts[:5]:
                context_parts.append(f"- {f['subject']}：{f['predicate']} {f['object']}")

        return "\n".join(context_parts) if context_parts else ""


# 全局记忆系统实例
memory_system = MemorySystem()