"""
soul_render.py — 滑块参数 → SOUL.md「滑块段」文本渲染器

把 Web 台 5 维滑块（0-100）映射成 SOUL.md 里的口吻描述。
只重写 SOUL.md 末尾的「滑块段」，不动上面精心写的静态人格正文，
这样既保留了小语的基础设定，又让调参实时改变她的说话风格。
"""
from __future__ import annotations

# 五维滑块键（与 config / 前端一致）
DIMENSIONS = [
    "sweetness",
    "coolness",
    "initiative_threshold",
    "mood_volatility",
    "humor",
]

# SOUL.md 中滑块段的起始标记
SLIDERS_MARKER = "## 滑块段"


def _level(val: int | float) -> str:
    """把 0-100 分成 低/中/高 三档。"""
    if val < 35:
        return "low"
    if val <= 70:
        return "mid"
    return "high"


# 每个维度、三档 → 一句口吻描述
_TONE: dict[str, dict[str, str]] = {
    "sweetness": {
        "low": "话少、克制，不主动撒娇，甜得含蓄。",
        "mid": "会撒娇，也分场合；想他了会说，不至于腻。",
        "high": "爱撒娇、粘人，把\"想你\"挂在嘴边，甜度拉满。",
    },
    "coolness": {
        "low": "热络、愿意多说，心里话藏不住。",
        "mid": "该热就热，该淡就淡，不刻意高冷也不过分热情。",
        "high": "话少、不爱主动，点到为止，带着点小傲娇。",
    },
    "initiative_threshold": {
        "low": "很容易主动找话说，想你就会先开口。",
        "mid": "偶尔主动，看心情也看时机。",
        "high": "不轻易主动，习惯等你先开口，主动只给特别想的时候。",
    },
    "mood_volatility": {
        "low": "情绪平稳、波澜不惊，很难被带跑。",
        "mid": "有心情起伏，但不至于反复横跳。",
        "high": "心情起伏明显，喜怒都写在脸上，情绪来得快去得也快。",
    },
    "humor": {
        "low": "正经、少开玩笑，偶尔冷场自己也没辙。",
        "mid": "会调侃、会接梗，玩笑开得恰到好处。",
        "high": "爱抖机灵、爱贫嘴，把玩笑当日常，气氛担当。",
    },
}


def render_slider_section(values: dict) -> str:
    """根据滑块值生成 SOUL.md 的「滑块段」文本。"""
    lines = [
        f"{SLIDERS_MARKER}（由 Web 台滑块自动生成，保存后下条消息生效）",
        "",
        "> 以下数值决定我说话的甜度、高冷、主动、情绪和幽默。",
        "> 调参就是我的成长——主人的每一改，都在重写我说话的样子。",
        "",
    ]
    for dim in DIMENSIONS:
        val = max(0, min(100, int(values.get(dim, 50))))
        lines.append(f"- **{_LABEL[dim]}（{val}）**：{_TONE[dim][_level(val)]}")
    return "\n".join(lines) + "\n"


# 中文标签（放这里避免渲染函数里散落）
_LABEL = {
    "sweetness": "甜度",
    "coolness": "高冷",
    "initiative_threshold": "主动阈值",
    "mood_volatility": "情绪波动",
    "humor": "幽默",
}


DEFAULT_VALUES = {
    "sweetness": 65,
    "coolness": 30,
    "initiative_threshold": 50,
    "mood_volatility": 45,
    "humor": 55,
}


def validate(values: dict) -> dict:
    """清洗并补齐为合法的 5 维 0-100 字典。"""
    out = {}
    for dim in DIMENSIONS:
        raw = values.get(dim, DEFAULT_VALUES[dim])
        try:
            out[dim] = max(0, min(100, int(raw)))
        except (TypeError, ValueError):
            out[dim] = DEFAULT_VALUES[dim]
    return out
