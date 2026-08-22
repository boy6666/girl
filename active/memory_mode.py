"""memory_mode.py — 记忆·检索盐度旋钮（爱语「记忆三模式」移植）。

config.yaml 顶层 memory.recall_mode（eager | auto | cautious）决定她**检索记忆这一口的咸淡**：
多勤于翻旧账、翻多深。这不是记忆本身上限，只是查的时候翻得多还是翻得少。
所选模式会渲染进 girl_workspace/PROACTIVE_INTAKE.md 的 §记忆 分块（BEGIN/END 标记之间），
吃饭时告诉她「怎么用记忆」，而不只是给她一个开关名。

三档各有社科依据（对齐项目已有的依恋轴）：
- eager   依恋焦虑者的「安全核查」：Anxious-preoccupied 更常做 reassurance seeking
          （hyperactivation）——她怕自己忘了和主人有关的事，聊到关键处就多翻几条垫底，
          翻不到也大方去检索。
- auto    多数人对自己的情景记忆是「需要时自动取用」的：想起就用，没想起且重要才检索，
          不整段复述记忆，只用它把话说准。
- cautious 高回避的「去激活」倾向（deactivating strategies）较少提取/分享依恋情绪记忆——
          她沉得住、不靠翻找撑场面，靠记得的聊；真卡住且重要才检索一次。
"""
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "config.yaml"
INTAKE_PATH = Path(__file__).resolve().parents[1] / "girl_workspace" / "PROACTIVE_INTAKE.md"

MODES = ("eager", "auto", "cautious")
DEFAULT_MODE = "auto"

_BEGIN = "<!-- BEGIN memory_recall -->"
_END = "<!-- END memory_recall -->"

GUIDANCE = {
    "eager": (
        "像一怕忘了你的人，聊到与他有关的要紧处，就先翻一两条相关记忆垫在心上"
        "（<search:关键词>），翻之前先自己想想，别把聊天变成查资料；"
        "心里没着落就大方说「<search:…>」，别硬扛。"
    ),
    "auto": (
        "想起就用，不整段复述记忆，只用它把话说准；没想起、这事又重要，"
        "就检索一次（<search:关键词>），翻完接着聊，不悬着。"
    ),
    "cautious": (
        "平时不主动翻，靠你自己记得的聊——记得的才是你；真正卡住、且这事对他重要，"
        "才检索一次（<search:关键词>）。别让翻找撑场面，稳一点。"
    ),
}


def load_mode(cfg_path: Path = CONFIG_PATH) -> str:
    """读 config.yaml memory.recall_mode；缺/非法 → auto。"""
    try:
        import yaml
        with cfg_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        mode = (data.get("memory") or {}).get("recall_mode", DEFAULT_MODE)
    except Exception:
        return DEFAULT_MODE
    return mode if mode in MODES else DEFAULT_MODE


def render_block(mode: str) -> str:
    """按所选模式渲染 §记忆 分块（BEGIN/END 包裹，可整体替换）。"""
    mode = mode if mode in MODES else DEFAULT_MODE
    intro = {
        "eager": "你像一怕忘了和他有关的事、聊到关键处就想先翻几条记忆垫底的人。",
        "auto": "你想起就用、没想起且重要才去检索的人。",
        "cautious": "你沉得住、不靠翻找撑场面的人。",
    }[mode]
    return (
        f"{_BEGIN}\n"
        f"## 记忆 · 检索的盐度（recall_mode = {mode}）\n"
        f"\n"
        f"**他调的是「{mode}」档**：{intro}\n"
        f"\n"
        f"{GUIDANCE[mode]}\n"
        f"\n"
        f"> recall_mode 只管「翻多勤、翻多深」这一口咸淡，你的记忆照常长、照常 QMD 检索；\n"
        f"> 翻到的是背景，别整段背出来给主人听，用得上才用。\n"
        f"{_END}"
    )


def apply_to_intake(mode: str | None = None, cfg_path: Path = CONFIG_PATH,
                    intake_path: Path = INTAKE_PATH) -> str | None:
    """把当前 recall_mode 渲染成 §记忆 分块，替换 PROACTIVE_INTAKE.md 里的同款分块。
    文件不存在→返回 None（不创建——学院契约文件不该由旋钮凭空生成）；失败静默返回 None。"""
    mode = (mode or load_mode(cfg_path))
    if mode not in MODES:
        return None
    block = render_block(mode)
    try:
        text = intake_path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None
    if _BEGIN in text and _END in text:
        text = text.split(_BEGIN, 1)[0] + block + text.split(_END, 1)[1]
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    try:
        intake_path.write_text(text, encoding="utf-8")
    except OSError:
        return None
    return block
