"""
向量数据库模块 - Chroma 存储记忆摘要向量
用于语义检索
"""
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings


class VectorDB:
    """向量数据库管理器"""

    def __init__(self, persist_dir: Optional[str] = None):
        if persist_dir is None:
            persist_dir = str(Path(__file__).parent.parent / "data" / "chroma")

        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        # 默认集合
        self.memory_collection = self.client.get_or_create_collection(
            name="memory_summaries",
            metadata={"description": "AI女友的记忆摘要向量"}
        )

    def add_memory(self, text: str, metadata: Dict[str, Any]) -> str:
        """添加记忆向量

        Args:
            text: 记忆文本内容
            metadata: 包含 id, timestamp, emotion_tag 等信息

        Returns:
            vector_id: 向量ID
        """
        vector_id = metadata.get('id', f"mem_{metadata.get('timestamp', '')}")

        self.memory_collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[vector_id]
        )

        return vector_id

    def search(self, query: str, n_results: int = 5,
               threshold: float = 0.7) -> List[Dict[str, Any]]:
        """语义检索记忆

        Args:
            query: 查询文本
            n_results: 返回数量
            threshold: 相似度阈值

        Returns:
            相关记忆列表
        """
        results = self.memory_collection.query(
            query_texts=[query],
            n_results=n_results
        )

        memories = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if 'distances' in results else 0
                similarity = 1 - distance  # Chroma 用 L2 距离

                if similarity >= threshold:
                    memories.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if 'metadatas' in results else {},
                        'similarity': similarity,
                        'id': results['ids'][0][i] if 'ids' in results else None
                    })

        return memories

    def delete(self, vector_id: str) -> bool:
        """删除记忆向量"""
        try:
            self.memory_collection.delete(ids=[vector_id])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """获取记忆数量"""
        return self.memory_collection.count()

    def clear(self):
        """清空所有记忆（谨慎使用）"""
        self.client.delete_collection("memory_summaries")
        self.memory_collection = self.client.get_or_create_collection(
            name="memory_summaries",
            metadata={"description": "AI女友的记忆摘要向量"}
        )


# 全局向量数据库实例
vector_db = VectorDB()