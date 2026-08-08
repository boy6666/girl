"""
对话引擎模块 - 调用云端 API 生成回复
"""
import asyncio
import httpx
from typing import List, Dict, Optional, Tuple
from app.config import config
from app.memory import memory_system
from app.database import db


class ChatEngine:
    """对话引擎"""

    def __init__(self):
        self.api_base = config.config.ai.chat_api_base
        self.model = config.config.ai.chat_model
        self.context_turns = config.config.memory.context_turns
        self._message_history: List[Dict[str, str]] = []

    def reset_history(self):
        """重置对话历史"""
        self._message_history = []

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        personality_prompt = config.get_personality_prompt()

        system_prompt = f"""{personality_prompt}

重要规则：
1. 说话要自然，像真人聊天一样，不要太正式
2. 可以适当撒娇、调侃，但要符合人格设定
3. 如果聊到之前记住的事情，可以提及
4. 回复长度适中，除非用户要求详细
5. 如果用户发送图片/语音，可以假装理解并回应

【当前时间】
{datetime.now().strftime('%Y年%m月%d日 %H:%M')}

请开始对话。"""

        return system_prompt

    def _build_context(self, current_message: str) -> str:
        """构建上下文（包含记忆）"""
        memory_context = memory_system.build_memory_context(current_message)
        if memory_context:
            return f"\n\n{'-' * 20}\n{memory_context}\n{'-' * 20}\n"
        return ""

    async def generate_response(self, user_message: str,
                                emotion_hint: str = None) -> Tuple[str, str]:
        """生成回复

        Returns:
            (回复文本, 情绪标签)
        """
        # 添加用户消息到历史
        self._message_history.append({
            "role": "user",
            "content": user_message
        })

        # 构建消息列表
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        # 添加上下文（记忆）
        context = self._build_context(user_message)
        if context:
            messages.append({
                "role": "system",
                "content": f"参考信息：{context}"
            })

        # 添加历史对话（保留最近 N 轮）
        history = self._message_history[-self.context_turns * 2:]
        messages.extend(history)

        # 调用 API
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.8,
                        "max_tokens": 500
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    assistant_message = result['choices'][0]['message']['content']

                    # 分析回复情绪
                    emotion = self._detect_emotion(assistant_message, emotion_hint)

                    # 添加助手回复到历史
                    self._message_history.append({
                        "role": "assistant",
                        "content": assistant_message
                    })

                    # 保存到记忆系统（异步，不阻塞）
                    asyncio.create_task(
                        memory_system.save_interaction(user_message, assistant_message, emotion)
                    )

                    return assistant_message, emotion

                else:
                    return "呜呜，网络好像不太好...", "sad"

        except Exception as e:
            print(f"API 调用失败: {e}")
            return "脑子有点卡壳了，等我缓缓...", "confused"

    def _detect_emotion(self, text: str, hint: str = None) -> str:
        """简单情绪检测"""
        if hint:
            return hint

        # 简单关键词匹配
        emotion_keywords = {
            'happy': ['开心', '高兴', '哈哈', '真好', '爱你', '喜欢', '棒', '好耶'],
            'sad': ['难过', '伤心', '呜呜', '委屈', '哭了', '唉'],
            'angry': ['生气', '哼', '讨厌', '烦', '不理你'],
            'shy': ['害羞', '脸红', '不好意思', '讨厌啦'],
            'cute': ['撒娇', '嘿嘿', '嘛', '啦'],
            'confused': ['？', '什么', '不懂', '哈？']
        }

        text_lower = text.lower()
        for emotion, keywords in emotion_keywords.items():
            if any(kw in text for kw in keywords):
                return emotion

        return 'neutral'

    async def generate_passive_message(self, topic_hint: str = None) -> str:
        """生成主动消息（不基于用户输入）"""
        # 可选的话题提示
        topics = [
            "突然想到一个好可爱的事情~",
            "刚才看到一只好可爱的猫猫！",
            "你在干嘛呀？有没有想我~",
            "今天天气好好哦，想出去散步",
            topic_hint or "突然好想跟你聊天~",
        ]

        system_prompt = f"""{config.get_personality_prompt()}

你是主动发起对话的一方。
请根据当前情境生成一条自然的、不重复的主动消息。
消息要简短（20-50字），像真正的女友一样自然地发起闲聊。
不要问太多问题，保持轻松的氛围。"""

        try:
            import random
            topic = random.choice(topics)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": topic}
                        ],
                        "temperature": 1.0,
                        "max_tokens": 100
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']

        except Exception as e:
            print(f"主动消息生成失败: {e}")

        # 备用消息
        return topic


# 全局对话引擎实例
chat_engine = ChatEngine()