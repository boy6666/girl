"""
微信接入模块 - 基于 ClawBot (腾讯官方微信插件)
官方文档: https://github.com/OpenClaw-Project/ClawBot
"""
import asyncio
import json
from typing import Optional, Callable
from datetime import datetime


class WeChatAdapter:
    """微信适配器 - 使用 ClawBot"""

    def __init__(self):
        self.client = None
        self._connected = False
        self._message_callback: Optional[Callable] = None
        self._ws_url = "ws://localhost:5031"  # ClawBot 默认 WebSocket 端口

    async def connect(self) -> bool:
        """连接微信 (ClawBot)"""
        try:
            import websockets

            async with websockets.connect(self._ws_url) as ws:
                self.client = ws
                self._connected = True
                print("✓ ClawBot 连接成功")

                # 监听消息
                async for message in ws:
                    data = json.loads(message)
                    await self._on_message(data)

        except ImportError:
            print("⚠ websockets 库未安装，请运行: pip install websockets")
            return False
        except ConnectionRefusedError:
            print("✗ 无法连接到 ClawBot，请确保 ClawBot 已启动并运行在 localhost:5031")
            return False
        except Exception as e:
            print(f"✗ ClawBot 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        self._connected = False
        if self.client:
            await self.client.close()

    def set_message_callback(self, callback: Callable):
        """设置消息接收回调"""
        self._message_callback = callback

    async def _on_message(self, message: dict):
        """处理微信消息"""
        try:
            # ClawBot 消息格式
            msg_type = message.get('msg_type', '')

            # 只处理私聊文本消息
            if msg_type != 'text' or message.get('is_group', False):
                return

            content = message.get('content', '').strip()
            sender_wxid = message.get('from_wxid', '')

            # 忽略空消息和自身消息
            if not content or sender_wxid == 'self':
                return

            print(f"[微信消息] {sender_wxid}: {content}")

            # 更新行为引擎状态
            from app.behavior import behavior_engine
            behavior_engine.on_user_message_received()

            # 处理消息并生成回复
            asyncio.create_task(self._process_and_reply(content, sender_wxid))

        except Exception as e:
            print(f"消息处理失败: {e}")

    async def _process_and_reply(self, content: str, sender_wxid: str):
        """处理消息并回复"""
        from app.chat import chat_engine

        # 检查是否为指令
        if content.startswith('/'):
            await self._handle_command(content, sender_wxid)
            return

        # 生成回复
        response, emotion = await chat_engine.generate_response(content)

        # 发送回复
        await self.send_text(sender_wxid, response)

        # 通知回调
        if self._message_callback:
            self._message_callback(sender_wxid, content, response, emotion)

    async def _handle_command(self, command: str, sender: str):
        """处理指令"""
        from app.chat import chat_engine
        from app.behavior import behavior_engine
        from app.database import db
        from app.vector_db import vector_db

        cmd = command.lower()

        if cmd == '/help':
            await self.send_text(sender, """📋 可用指令：
/help - 显示帮助
/reset - 重置对话历史
/status - 查看我的状态
/memory - 查看记忆数量
/dream - 触发梦境消息（测试）""")

        elif cmd == '/reset':
            chat_engine.reset_history()
            await self.send_text(sender, "好啦，当作我们第一次聊天~")

        elif cmd == '/status':
            status = behavior_engine.get_status()
            await self.send_text(sender, f"""📊 我的状态：
💪 精力：{status['energy']}%
😊 情绪：{status['mood']}%
💬 社交需求：{status['social_need']}%""")

        elif cmd == '/memory':
            facts = db.get_facts()
            vectors = vector_db.count()
            await self.send_text(sender, f"""📝 记忆统计：
🔢 事实数量：{len(facts)}
🧠 向量数量：{vectors}""")

        elif cmd == '/dream':
            response = await chat_engine.generate_passive_message("我刚做了一个奇怪的梦...")
            await self.send_text(sender, f"刚做了个梦：{response}")

    async def send_text(self, receiver_wxid: str, content: str) -> bool:
        """发送文本消息"""
        if not self._connected or not self.client:
            return False

        try:
            message = {
                "action": "send_text",
                "to_wxid": receiver_wxid,
                "content": content
            }
            await self.client.send(json.dumps(message))
            print(f"[发送消息] → {receiver_wxid}: {content}")
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            return False

    async def send_image(self, receiver_wxid: str, image_path: str) -> bool:
        """发送图片消息"""
        if not self._connected or not self.client:
            return False

        try:
            # 读取图片并转为 base64
            import base64
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()

            message = {
                "action": "send_image",
                "to_wxid": receiver_wxid,
                "image_base64": img_data
            }
            await self.client.send(json.dumps(message))
            print(f"[发送图片] → {receiver_wxid}")
            return True
        except Exception as e:
            print(f"发送图片失败: {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected


# 全局微信适配器实例
wechat_adapter = WeChatAdapter()