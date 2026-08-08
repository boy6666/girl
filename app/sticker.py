"""
表情包系统模块
根据对话情绪自动匹配并发送表情包
"""
import os
import random
from pathlib import Path
from typing import Optional, List
from enum import Enum


class Emotion(Enum):
    """情绪枚举"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SHY = "shy"
    CUTE = "cute"
    CONFUSED = "confused"
    NEUTRAL = "neutral"
    LOVE = "love"
    ANXIOUS = "anxious"


class StickerSystem:
    """表情包系统"""

    # 情绪到文件夹的映射
    EMOTION_MAPPING = {
        Emotion.HAPPY: ["happy", "开心", "笑"],
        Emotion.SAD: ["sad", "难过", "伤心"],
        Emotion.ANGRY: ["angry", "生气", "怒"],
        Emotion.SHY: ["shy", "害羞", "脸红"],
        Emotion.CUTE: ["cute", "可爱", "萌"],
        Emotion.CONFUSED: ["confused", "疑惑", "懵"],
        Emotion.NEUTRAL: ["neutral", "普通"],
        Emotion.LOVE: ["love", "爱心"],
        Emotion.ANXIOUS: ["anxious", "焦虑", "担心"],
    }

    def __init__(self, sticker_dir: Optional[str] = None):
        if sticker_dir is None:
            sticker_dir = str(Path(__file__).parent.parent / "data" / "stickers")
        self.sticker_dir = Path(sticker_dir)
        self.sticker_dir.mkdir(parents=True, exist_ok=True)
        self._emotion_stickers: dict[Emotion, List[Path]] = {}
        self._build_index()

    def _build_index(self):
        """构建表情包索引"""
        for emotion, folders in self.EMOTION_MAPPING.items():
            stickers = []
            for folder in folders:
                folder_path = self.sticker_dir / folder
                if folder_path.exists():
                    stickers.extend(folder_path.glob("*.png"))
                    stickers.extend(folder_path.glob("*.jpg"))
                    stickers.extend(folder_path.glob("*.gif"))
            self._emotion_stickers[emotion] = stickers

        for emotion in Emotion:
            if emotion not in self._emotion_stickers:
                self._emotion_stickers[emotion] = []

    def get_sticker_path(self, emotion: str) -> Optional[str]:
        """根据情绪获取随机表情包路径"""
        try:
            emotion_enum = Emotion(emotion.lower())
        except ValueError:
            emotion_enum = Emotion.NEUTRAL

        stickers = self._emotion_stickers.get(emotion_enum, [])
        if not stickers:
            for similar in [Emotion.CUTE, Emotion.HAPPY, Emotion.LOVE]:
                stickers = self._emotion_stickers.get(similar, [])
                if stickers:
                    break

        if not stickers:
            return None
        return str(random.choice(stickers))

    def get_random_sticker(self) -> Optional[str]:
        """获取随机表情包"""
        all_stickers = [s for stickers in self._emotion_stickers.values() for s in stickers]
        return str(random.choice(all_stickers)) if all_stickers else None

    def add_sticker(self, emotion: str, file_path: str) -> bool:
        """添加表情包"""
        try:
            emotion_enum = Emotion(emotion.lower())
        except ValueError:
            emotion_enum = Emotion.NEUTRAL

        folders = self.EMOTION_MAPPING.get(emotion_enum, ["neutral"])
        target_dir = self.sticker_dir / folders[0]
        target_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        file_name = Path(file_path).name
        dest_path = target_dir / file_name
        shutil.copy(file_path, dest_path)
        self._emotion_stickers[emotion_enum].append(dest_path)
        return True

    def get_stats(self) -> dict:
        """获取表情包统计"""
        return {e.value: len(s) for e, s in self._emotion_stickers.items()}


sticker_system = StickerSystem()