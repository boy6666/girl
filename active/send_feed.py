"""send_feed.py — 把「小语真正发出去的每一条消息」闭环进状态机，并区分两类：
  __REPLY__ 她在回主人的一条新消息  → on_user_reply（清未回/断 awaiting/归零渴望）
  __SELF__  她自己主动发的          → on_active_sent（记主动/冷却/awaiting/耗精力）
  __PAUSE__ 链路暂停信号（如微信被停/主人按下暂停）→ 暂停主动循环，卡不攒
  __RESUME__ 解除暂停；真回（__REPLY__）也自动醒

单出口架构下 Python 不读微信；这几类信号只能由看得见"她到底发了什么"的
OpenClaw 侧（girl）在真实发出消息/收发暂停时往 memory/send_feed.md 写一行，心跳在这里消费。
与旧 reply_feed 不同：一次一发、必带类型，把「回」和「主动」从机制上分开，
不再靠"写不写标记"的自觉决定该归到哪一类。

暂停 = 物理通道信号，不是心理卫门：2026-08-21 grill 拍板拆掉的四扇卫门不回魂，
paused 只挡「主动窗口」这个对外开口（不拼卡不 inject），晚间反思/日记/梦/生长照常。
"""
from datetime import datetime
from pathlib import Path

from . import state_machine

SEND_PATH = (Path(__file__).resolve().parents[1]
             / "girl_workspace" / "memory" / "send_feed.md")
_COMMENT_PREFIX = ("<!--", "#")
REPLY = "__REPLY__"
SELF = "__SELF__"
PAUSE = "__PAUSE__"
RESUME = "__RESUME__"
_KINDS = (REPLY, SELF, PAUSE, RESUME)
_HEADER = ("<!-- 发送日志：girl 每次真正发出一条消息就记一行，带类型。\n"
           "  __REPLY__ 在回主人的一条新消息（同时自动解除暂停）；__SELF__ 自己主动发。\n"
           "  __PAUSE__ 通道暂停（如微信被停），暂停主动窗口；__RESUME__ 解除。\n"
           "Python 心跳读后打回状态机并清空，绝不残留 -->")


def _lines(path: Path) -> list:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [ln.strip() for ln in lines
            if ln.strip() and not ln.lstrip().startswith(_COMMENT_PREFIX)]


def pending_kinds(path=None) -> list:
    """标记文件里的全部待消费标记（按出现顺序）。"""
    return [ln for ln in _lines(path or SEND_PATH) if ln in _KINDS]


def has_pending(path=None) -> bool:
    return bool(pending_kinds(path))


def signal(kind: str, path=None) -> bool:
    """主动写一条发送日志标记（CLI pause/resume / 手动信号用），保留注释头、追加一行。"""
    path = path or SEND_PATH
    if kind not in _KINDS:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            text = path.read_text(encoding="utf-8").rstrip("\n")
            text = text + "\n" + kind + "\n"
        else:
            text = _HEADER + "\n" + kind + "\n"
        path.write_text(text, encoding="utf-8")
        return True
    except OSError:
        return False


def consume(state, config, path=None, now=None):
    """读一次发送日志；按顺序把每条标记打回对应状态变迁，然后清空文件。
    返回 (new_state, kinds) —— kinds 为实际消费到的标记列表（顺序保留）。"""
    path = path or SEND_PATH
    kinds = pending_kinds(path)
    if not kinds:
        return state, []
    now = now or datetime.now()
    s = state
    for kind in kinds:
        if kind == REPLY:
            s = state_machine.on_user_reply(s, config, now=now, quality=0.0)
            s["paused"] = False           # 真回 = 通道复活，自动醒
        elif kind == SELF:
            s = state_machine.on_active_sent(s, config, now=now)
        elif kind == PAUSE:
            s["paused"] = True            # 链路暂停：主动窗口停手（不拼卡不 inject）
        elif kind == RESUME:
            s["paused"] = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_HEADER + "\n", encoding="utf-8")
    except OSError:
        pass
    return s, kinds
