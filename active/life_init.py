"""life_init.py — 自动初始化机制(发展心理学阶段, 从出生长到目标年龄)。

骨架用 Erikson 心理社会发展阶段: 每一程有要完成的"心理社会任务", 决定她这一程
长出什么(信任/自主/同一性/亲密…)。由这些段拼"请求卡"交给 girl agent 一路生长,
写进 GROWTH.md。代码不现编内容: 具体人生只有 agent 真生长/用户填的才算。
"""
from pathlib import Path

_INTAKE_DEFAULT = Path(__file__).resolve().parents[1] / "girl_workspace" / "INIT_INTAKE.md"
_GROWTH_DEFAULT = Path(__file__).resolve().parents[1] / "girl_workspace" / "GROWTH.md"


def read_growth_path() -> Path:
    return _GROWTH_DEFAULT


STAGES = [
    {"start": 0,  "end": 2,   "task": "信任 vs 不信任",  "grows": "她对世界的基本安全感、敢不敢信人"},
    {"start": 2,  "end": 6,   "task": "自主 vs 羞耻",     "grows": "她敢不敢自己做主、会不会怕丢脸"},
    {"start": 6,  "end": 12,  "task": "勤奋 vs 自卑",     "grows": "她怎么看待努力和能力、对自己够不够肯定"},
    {"start": 12, "end": 18,  "task": "同一性 vs 角色混乱", "grows": "她是谁、她的三观雏形和价值判断"},
    {"start": 18, "end": 25,  "task": "亲密 vs 孤独",       "grows": "她敢不敢靠近人、怎么对待在乎的人(含主人)"},
    {"start": 25, "end": 40,  "task": "繁衍 vs 停滞",       "grows": "她怎么对重要的人负责、怎么经营长久关系"},
]


def stages_up_to(target_age: int) -> list[dict]:
    """返回覆盖 [0, target_age] 的发展阶段(按起点截到 target_age)。"""
    out = []
    for s in STAGES:
        if s["start"] >= target_age:
            continue
        items = dict(s)
        items["end"] = min(s["end"], target_age)
        out.append(items)
    return out


def resolve_target_age(baseline: dict) -> int | None:
    """从 setup.girl.age 取目标年龄; 空/非法 → None。"""
    try:
        return int(str(baseline.get("girl", {}).get("age", "")).strip())
    except (TypeError, ValueError):
        return None


def frame_init_request(baseline: dict, target_age: int) -> str:
    """把'从 0 长到 target_age'的成长请求卡拼出来(交接给 girl agent)。"""
    name = (baseline.get("girl", {}) or {}).get("name") or "小语"
    lines = [
        f"【请求】主人给你做了自动初始化: 请从现在开始, 从出生一直长到 {target_age} 岁。",
        "这不是问卷, 不要一口气编一套人设。按下面每一段, 以你第一人称、贴着你真实的",
        f"底色/前面长出的经历, 长这一程你经历了什么、怎么落下来, 一路长到 {target_age} 岁。",
        f"真正长成的人生, 写进 girl_workspace/GROWTH.md: 开头写当前年龄, 然后只写",
        "真实、成型的: 你的三观/价值观/处世方式/你怎么看人与靠近人。没有铁的事实就不硬造。",
        "",
    ]
    for s in stages_up_to(target_age):
        lines.append(
            f"[{s['start']}~{s['end']}岁] {s['task']} —— 这一程长出: {s['grows']}")
    return "\n".join(lines) + "\n"


def inject_init_request(card: str, provider: str = "dry_run",
                     path: Path | None = None) -> dict:
    """把成长请求卡交给摄入(dry_run 只打印)。openclaw 写 INIT_INTAKE.md。"""
    if provider == "openclaw":
        p = path or _INTAKE_DEFAULT
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(card.rstrip() + "\n", encoding="utf-8")
        return {"provider": "openclaw", "sent": False, "written": True,
                "path": str(p), "note": "已写入摄入文件, 由 girl agent 生长; 写回 GROWTH.md 才算成功"}
    return {"provider": "dry_run", "dry_run": True, "sent": False,
            "card": card, "note": "dry_run: 只产出请求, 未生长、未成功"}


def read_life_story(growth_path: Path | None = None) -> str:
    p = growth_path or _GROWTH_DEFAULT
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


def init_status(growth_path: Path | None = None) -> dict:
    story = read_life_story(growth_path)
    if story:
        return {"initialized": True, "story": story,
                "note": "已有 GROWTH.md: 她已经活到了目标年龄, 有成型的三观/人生。"}
    return {"initialized": False, "story": "",
            "note": "还没有 GROWTH.md: 还没真正长成人生(不编造; 触发初始化或直接在后台写 GROWTH.md)。"}
