"""
主动行为引擎模块 - 模拟 AI 女友的自主行为
包括精力、情绪、社交需求等状态变量
"""
import asyncio
import random
from datetime import datetime
from typing import Optional, Callable
from app.config import config
from app.chat import chat_engine
from app.database import db


class ActiveBehaviorEngine:
    """主动行为引擎"""

    # 随机生活事件
    RANDOM_EVENTS = [
        {"type": "dream", "text": "刚才做了一个好奇怪的梦...", "weight": 10},
        {"type": "insomnia", "text": "睡不着，突然好想你...", "weight": 15},
        {"type": "cute_animal", "text": "刚看到一只超可爱的狗狗！", "weight": 20},
        {"type": "food", "text": "好想吃火锅呀...", "weight": 15},
        {"type": "weather", "text": "今天天气好舒服~", "weight": 20},
        {"type": "work", "text": "忙完啦～终于有空了", "weight": 10},
        {"type": "bored", "text": "好无聊哦，你在干嘛呀？", "weight": 25},
        {"type": "miss", "text": "突然有点想你了呢...", "weight": 20},
        {"type": "funny", "text": "刚看到一个好好笑的视频，笑死我了哈哈哈", "weight": 15},
        {"type": "flower", "text": "路上看到一朵好漂亮的花~", "weight": 10},
    ]

    def __init__(self):
        self.ab_config = config.config.active_behavior

        # 状态变量
        self.energy = self.ab_config.energy
        self.mood = self.ab_config.mood
        self.social_need = self.ab_config.social_need

        # 内部状态
        self._running = False
        self._last_active_message_time: Optional[datetime] = None
        self._last_check_time = datetime.now()
        self._on_send_message: Optional[Callable] = None

    def set_message_callback(self, callback: Callable[[str], None]):
        """设置消息回调（用于发送到微信）"""
        self._on_send_message = callback

    async def start(self):
        """启动主动行为引擎"""
        self._running = True
        asyncio.create_task(self._state_update_loop())
        asyncio.create_task(self._behavior_loop())

    async def stop(self):
        """停止引擎"""
        self._running = False

    async def _state_update_loop(self):
        """状态更新循环 - 每秒更新状态"""
        while self._running:
            try:
                current_hour = datetime.now().hour
                ab = self.ab_config

                # 时间流逝，精力下降
                self.energy = max(0, self.energy - 0.1)

                # 睡眠时精力恢复
                if ab.late_night_start <= current_hour or current_hour < ab.early_morning_end:
                    if self.energy < 30:
                        self.energy = min(100, self.energy + 0.5)
                else:
                    # 白天活跃
                    if self.energy > 50:
                        self.mood = min(100, self.mood + 0.05)

                # 社交需求随时间增长
                if self._last_active_message_time:
                    seconds_since = (datetime.now() - self._last_active_message_time).seconds
                    if seconds_since > ab.cooldown_seconds:
                        self.social_need = min(100, self.social_need + 0.2)

                await asyncio.sleep(1)

            except Exception as e:
                print(f"状态更新失败: {e}")

    async def _behavior_loop(self):
        """行为决策循环 - 每分钟检查是否主动发消息"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次

                if self._should_send_active_message():
                    await self._send_active_message()

            except Exception as e:
                print(f"行为循环失败: {e}")

    def _should_send_active_message(self) -> bool:
        """判断是否应该主动发消息"""
        ab = self.ab_config

        # 精力不足不打扰
        if self.energy < 20:
            return False

        # 非深夜检查
        current_hour = datetime.now().hour
        is_late_night = ab.late_night_start <= current_hour or current_hour < ab.early_morning_end

        if is_late_night and not ab.allow_late_night:
            return False

        # 精力低但深夜时只发低沉内容
        if is_late_night and self.energy < 40:
            return self.social_need > 80 and random.random() < 0.3

        # 正常情况：社交需求 + 随机概率
        trigger_prob = ab.initiative_threshold + self.social_need - 50
        trigger_prob = max(5, min(60, trigger_prob))

        # 如果距离上次消息太久，概率增加
        if self._last_active_message_time:
            minutes_since = (datetime.now() - self._last_active_message_time).seconds / 60
            if minutes_since > 120:  # 2小时以上
                trigger_prob += 20

        return random.random() * 100 < trigger_prob

    async def _send_active_message(self):
        """发送主动消息"""
        try:
            # 随机选择事件或直接生成消息
            if random.random() < 0.7:
                # 从预设事件中选择
                message = self._generate_event_message()
            else:
                # AI 生成
                message = await chat_engine.generate_passive_message()

            # 凌晨内容调整
            current_hour = datetime.now().hour
            if (self.ab_config.late_night_start <= current_hour or
                current_hour < self.ab_config.early_morning_end):
                if self.energy < 50:
                    # 精力低时内容偏少、偏想念
                    if "想你" not in message and "梦" not in message:
                        message = f"睡不着... {message}"

            # 发送消息
            if self._on_send_message:
                self._on_send_message(message)

            # 更新状态
            self._last_active_message_time = datetime.now()
            self.social_need = max(0, self.social_need - 30)
            self.energy = max(0, self.energy - 5)

            # 记录日志
            db.log_event("initiative", message, {
                "energy": self.energy,
                "mood": self.mood,
                "social_need": self.social_need
            })

        except Exception as e:
            print(f"发送主动消息失败: {e}")

    def _generate_event_message(self) -> str:
        """根据状态生成事件消息"""
        current_hour = datetime.now().hour
        is_late_night = (self.ab_config.late_night_start <= current_hour or
                        current_hour < self.ab_config.early_morning_end)

        # 根据时间过滤事件
        available_events = self.RANDOM_EVENTS

        if is_late_night:
            # 深夜优先失眠、梦境相关
            available_events = [e for e in self.RANDOM_EVENTS
                              if e['type'] in ['dream', 'insomnia', 'miss']]

        # 加权随机选择
        weights = [e['weight'] for e in available_events]
        event = random.choices(available_events, weights=weights)[0]

        return event['text']

    def on_user_message_received(self):
        """用户发消息时的回调 - 更新状态"""
        self._last_active_message_time = datetime.now()
        self.social_need = max(0, self.social_need - 20)
        self.energy = min(100, self.energy + 2)

    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "energy": round(self.energy, 1),
            "mood": round(self.mood, 1),
            "social_need": round(self.social_need, 1),
            "last_active_time": self._last_active_message_time.isoformat()
                              if self._last_active_message_time else None
        }


# 全局主动行为引擎实例
behavior_engine = ActiveBehaviorEngine()