"""life_content.py — 小语的生活内容库 data/life_content.yaml（Web「她的一天」页可编辑）。"""
import copy
from pathlib import Path

import yaml

LIFE_CONTENT_PATH = Path(__file__).resolve().parents[1] / "data" / "life_content.yaml"

BUCKETS = ("morning", "work", "afternoon", "evening")

DEFAULT_CONTENT = {
    "habits": [
        "喜欢猫，路上看到的猫都会多看两眼",
        "每周三傍晚去公园散步",
        "最近在追一部剧，还没看到结尾",
    ],
    "favorites": {
        "color": "暖色调，偏爱橘色",
        "food": "咖啡和栗子",
    },
    "schedule": {"wake": 7},
    "buckets": {
        "morning": [
            "晨跑二十分钟，回来冲了杯热咖啡",
            "赖了会儿床，刷手机看到只猫",
            "起了个大早，把昨儿没看完的书看完了",
        ],
        "work": [
            "手里那摊活总算弄完一段，腰都直了",
            "开了一上午的会，脑子嗡嗡的",
            "写东西卡了半天，刚有点眉目",
        ],
        "afternoon": [
            "楼下那家店新出的栗子味好香，没忍住",
            "路过看到晚霞，拍了一张",
            "散步被风一吹，又想起之前那件事",
        ],
        "evening": [
            "洗完澡窝在床上，今天有点累",
            "追的剧更新了，憋着没忍住先看了",
            "又觉得一个人待着有点空",
        ],
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
                out["buckets"][b] = data["buckets"][b]
    return out


def save_content(content: dict, path: Path = LIFE_CONTENT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")
