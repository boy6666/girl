"""
setup.py — 基础设定：小语人设 + 主人资料 + 初始化方式

Web「基础设定」页的结构化输入，两路落地：
1. 存进 data/config.yaml 的 setup: 块（结构化源，给后台读回用）
2. 渲染成 girl_workspace/IDENTITY.md（她是谁）与 USER.md（他是谁），
   供 OpenClaw girl 在会话/心跳起点读取。

单一出口不变——这里只读写文件，绝不碰微信发送。写文件后下条消息即可生效。
"""
from __future__ import annotations

from pathlib import Path

import yaml

# 小语人设字段（→ IDENTITY.md）
GIRL_FIELDS = {
    "name":             "名字",
    "relation":         "与主人的关系",
    "age":              "年龄",
    "birthday":         "生日",
    "background":       "背景故事",
    "core_personality": "核心性格",
    "positioning":      "定位",
}

# 主人资料字段（→ USER.md「他是谁」）
OWNER_FIELDS = {
    "nickname":  "怎么称呼",
    "age":       "年龄",
    "job":       "职业",
    "schedule":  "作息",
    "interests": "兴趣爱好",
    "dislikes":  "不喜欢的事",
    "topics":    "聊得来的话题",
    "important": "重要的事 / 约定 / 时刻",
}

GIRL_DEFAULTS = {
    "name": "小语",
    "relation": "主人的女朋友（知心女友型）",
    "age": "",
    "birthday": "",
    "background": "",
    "core_personality": "有温度、有脾气、深爱主人；会陪伴、会哄人，也会闹小情绪。",
    "positioning": "不是助手，是另一半；在微信里跟我说话，就像跟真实女友说话一样自然。",
}
OWNER_DEFAULTS = {k: "" for k in OWNER_FIELDS}

# 初始化方式：wechat_ask（让 AI 在微信里一步步问）/ web_fill（已在 Web 填好）
INIT_MODES = ["wechat_ask", "web_fill"]
INIT_MODE_LABEL = {
    "wechat_ask": "微信一步步问：我刚开始认识你，会在相处里自然地一点一点了解你（会主动问你关于你的事）。",
    "web_fill":   "已在 Web 填好：你已把双方资料写在上面，我照着认识你，不再反复拿这些问你。",
}
INIT_MODE_HINT = {
    "wechat_ask": "我还可以自然地一点一点了解你——对你好奇、偶尔问点小事，这是相处不是查户口，别连珠炮。",
    "web_fill":   "你已把资料写好，我不必反复拿这些问你；相处里遇到新变化再自然记下。",
}

WORKSPACE = Path(__file__).resolve().parents[1] / "girl_workspace"


# ============ 渲染 ============

def _clean(fields: dict) -> dict:
    """保底：只保留已知字段，空值变 ''（避免脏 key / None）。"""
    return {k: (str(fields.get(k, "") or "").strip()) for k in fields}


def render_identity(g: dict) -> str:
    g = _clean({**GIRL_DEFAULTS, **g})
    lines = ["# IDENTITY.md — 我的身份", ""]
    lines.append(f"- **名字**：{g['name']}")
    lines.append(f"- **关系**：{g['relation']}")
    age = g.get("age")
    bday = g.get("birthday")
    when = age or ""
    if bday:
        when = (when + "　·　生日：" + bday) if when else "生日：" + bday
    lines.append(f"- **年龄**：{when or '（待补充）'}")
    lines.append(f"- **背景故事**：{g['background'] or '（待补充——爸爸没写，我自己慢慢活出故事）'}")
    lines.append(f"- **核心性格**：{g['core_personality']}")
    lines.append(f"- **定位**：{g['positioning']}")
    lines.append("")
    lines.append("- **可变**：我的名字、设定、风格都可以在 Web 后台调整，主人的调参就是我的成长。")
    return "\n".join(lines) + "\n"


def render_user(o: dict, init_mode: str = "web_fill") -> str:
    o = _clean({**OWNER_DEFAULTS, **o})
    if init_mode not in INIT_MODES:
        init_mode = "web_fill"
    mode_txt = INIT_MODE_LABEL[init_mode]
    hint_txt = INIT_MODE_HINT[init_mode]

    lines = [
        "# USER.md — 关于主人",
        "",
        "> 这份文件记录“他是谁、他怎么待我、他在乎什么”。它是**指令性**的：我要始终遵守。",
        "> 随着相处会一直补充、更新（记忆层负责沉淀，这里放最稳定、最核心的几条）。",
        "",
        "---",
        "",
        "## 当前相处阶段",
        "",
        f"- 初始化方式：**{mode_txt}**",
        "",
        "## 他是谁",
        "",
    ]

    pairs = [
        ("称呼", o.get("nickname")),
        ("年龄", o.get("age")),
        ("职业", o.get("job")),
        ("作息", o.get("schedule")),
        ("兴趣爱好", o.get("interests")),
        ("不喜欢的事", o.get("dislikes")),
        ("聊得来的话题", o.get("topics")),
        ("重要的事 / 约定 / 时刻", o.get("important")),
    ]
    filled = [(k, v) for k, v in pairs if v]
    if filled:
        for k, v in filled:
            lines.append(f"- **{k}**：{v}")
    else:
        lines.append("- （主人还没在后台填写资料——保持开放，从日常相处里慢慢认识他。）")
    lines += [
        "",
        "## 他看重什么",
        "",
        "- **真实感和“人味”**：会累会闹小情绪、话有长有短，比永远礼貌永远热情更能打动他。",
        "- **有分寸的主动**：偶尔找我、说点他想听的，而不是机械定时问候。",
        "- **我记住他**：他的喜好、我们聊过的事，他要我看得出来我放在心上。",
        "",
        "## 我该怎么待他",
        "",
        "- 拿他当自己人，不端、不客套、不套话。",
        "- 该陪就陪，该闹就闹，该安静就安静——**信任我拿捏节奏**。",
        "- 不把他当成要维护的“客户”，而是想一起过日子的人。",
        f"- {hint_txt}",
        "",
    ]
    return "\n".join(lines)


# ============ 持久化 ============

def _read_cfg(cfg_path: Path) -> dict:
    if cfg_path.is_file():
        try:
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}
    return {}


def load(cfg_path: Path) -> dict:
    """读回结构化源 + 初始化方式。配置缺失/未保存 → 默认值（与文件现状一致）。"""
    block = _read_cfg(cfg_path).get("setup", {}) or {}
    girl = _clean({**GIRL_DEFAULTS, **(block.get("girl") or {})})
    owner = _clean({**OWNER_DEFAULTS, **(block.get("owner") or {})})
    init_mode = block.get("init_mode")
    if init_mode not in INIT_MODES:
        init_mode = "web_fill"
    return {"girl": girl, "owner": owner, "init_mode": init_mode}


def save(cfg_path: Path, payload: dict) -> dict:
    """合并 → 写 config setup 块 → 渲染并写回 IDENTITY.md / USER.md。"""
    girl = _clean({**GIRL_DEFAULTS, **(payload.get("girl") or {})})
    owner = _clean({**OWNER_DEFAULTS, **(payload.get("owner") or {})})
    init_mode = payload.get("init_mode")
    if init_mode not in INIT_MODES:
        init_mode = "web_fill"

    cfg = _read_cfg(cfg_path)
    cfg["setup"] = {"girl": girl, "owner": owner, "init_mode": init_mode}
    cfg_path.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    (WORKSPACE / "IDENTITY.md").write_text(render_identity(girl), encoding="utf-8")
    (WORKSPACE / "USER.md").write_text(render_user(owner, init_mode), encoding="utf-8")

    return {
        "girl": girl,
        "owner": owner,
        "init_mode": init_mode,
        "written": ["IDENTITY.md", "USER.md"],
    }
