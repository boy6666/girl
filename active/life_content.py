"""life_content.py — 小语的生活内容库 data/life_content.yaml（Web「她的一天」页可编辑）。

设计原则（用户确认）：不做死板可爱模板池。这里只是「类别骨架」，短语一律由
用户在 web 页填入小语的真实生活、或由 LLM 真生长给出；代码不现编内容。
四段 bucket 依据社科维系策略归类（Stafford & Canary 日常仪式 routine 锚点 +
Gable & Reis 积极事件分享），默认留空待填。
"""
import copy
from pathlib import Path

import yaml

LIFE_CONTENT_PATH = Path(__file__).resolve().parents[1] / "data" / "life_content.yaml"

BUCKETS = ("morning", "work", "afternoon", "evening")

# 默认只有结构，无现编内容：用户在 web 里填小语的真实生活。
DEFAULT_CONTENT = {
    "habits": [],          # 她的习惯（示例在 web 页提示填）——长久的底色
    "favorites": {},       # 她的偏好（颜色/吃的/地方…）
    "schedule": {"wake": 7},   # 作息骨架：起床时间（结构性默认，可改）
    "buckets": {
        "morning": [],     # 晨间仪式锚点
        "work": [],        # 日常劳作
        "afternoon": [],   # 午后闲暇
        "evening": [],     # 晚间收尾
    },
}


def load_content(path: Path = LIFE_CONTENT_PATH) -> dict:
    out = copy.deepcopy(DEFAULT_CONTENT)
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        for k in ("habits", "favorites", "schedule"):
            if data.get(k):
                out[k] = data[k]
        for b in BUCKETS:
            if data.get("buckets", {}).get(b):
                out["buckets"][b] = data["buckets"][b][:25]
    return out


def save_content(content: dict, path: Path = LIFE_CONTENT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
