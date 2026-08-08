"""
项目配置文件加载器
负责从 config.yaml 读取配置，支持热重载
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class PersonalityConfig(BaseModel):
    sweetness: int = 65
    coolness: int = 30
    initiative_threshold: int = 50
    mood_volatility: int = 45
    humor: int = 55


class ActiveBehaviorConfig(BaseModel):
    energy: int = 80
    mood: int = 75
    social_need: int = 40
    cooldown_seconds: int = 300
    allow_late_night: bool = True
    late_night_start: int = 23
    early_morning_end: int = 6


class MemoryConfig(BaseModel):
    context_turns: int = 10
    summary_max_length: int = 200
    similarity_threshold: float = 0.7
    daily_memory_limit: int = 50


class AIConfig(BaseModel):
    chat_model: str = "deepseek-chat"
    chat_api_base: str = "https://api.deepseek.com/v1"
    local_model: str = "qwen2.5:1.5b"
    local_api_base: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"


class WeChatConfig(BaseModel):
    protocol_version: str = "v3"
    auto_accept_friend: bool = False
    private_only: bool = True


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    ws_ping_interval: int = 30000


class AppConfig(BaseModel):
    personality: PersonalityConfig = PersonalityConfig()
    active_behavior: ActiveBehaviorConfig = ActiveBehaviorConfig()
    memory: MemoryConfig = MemoryConfig()
    ai: AIConfig = AIConfig()
    wechat: WeChatConfig = WeChatConfig()
    server: ServerConfig = ServerConfig()


class ConfigManager:
    """配置管理器，支持热重载"""

    _instance: Optional['ConfigManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config_path = Path(__file__).parent.parent / "data" / "config.yaml"
        self._config: Optional[AppConfig] = None
        self._observers: list = []
        self._load_config()

    def _load_config(self) -> None:
        """从YAML文件加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    self._config = AppConfig(**data)
                else:
                    self._config = AppConfig()
        else:
            self._config = AppConfig()
            self._save_config()

    def _save_config(self) -> None:
        """保存配置到YAML文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config.model_dump(), f, allow_unicode=True, default_flow_style=False)

    @property
    def config(self) -> AppConfig:
        return self._config

    def update(self, section: str, updates: Dict[str, Any]) -> None:
        """更新配置项并保存"""
        if not hasattr(self._config, section):
            raise ValueError(f"Unknown config section: {section}")

        section_obj = getattr(self._config, section)
        for key, value in updates.items():
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
            else:
                raise ValueError(f"Unknown key '{key}' in section '{section}'")

        self._save_config()
        self._notify_observers(section)

    def get_personality_prompt(self) -> str:
        """生成人格描述 Prompt"""
        p = self._config.personality
        return f"""你是一个性格独特的AI女友，特点是：
- 甜度: {"偏高，很会撒娇" if p.sweetness > 60 else "适中" if p.sweetness > 30 else "偏冷淡"}
- 性格: {"有点高冷" if p.coolness > 60 else "热情主动" if p.coolness < 30 else "温柔体贴"}
- 幽默感: {"很强，擅长俏皮话" if p.humor > 60 else "适度" if p.humor > 30 else "较少"}
- 情绪: {"波动较大" if p.mood_volatility > 60 else "相对稳定"}

请根据以上性格特点，用自然的语气回复消息，像真正的女友一样。"""

    def _notify_observers(self, section: str):
        for callback in self._observers:
            callback(section)


# 全局配置实例
config = ConfigManager()