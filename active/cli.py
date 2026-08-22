"""active/cli.py — 主动链路手动测试 CLI（web 无假身的替代）。

决策（2026-08-21 grill）：主动窗口触发只剩状态机+她本人，web「现在就推」按钮已拆。
手动试跑走 CLI 直敲状态机内部接口，不借 web 假身替她开口。

用法:
    python -m active.cli nudge [--provider dry_run|openclaw]
    python -m active.cli tick
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import (config as cfgmod, state_store, state_machine,
               life_content, life_journal, motivation, injector, send_feed,
               scheduler, inject_channels)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = DATA / "config.yaml"
STATE = DATA / "state.json"
CONTENT = DATA / "life_content.yaml"


def out(text: str) -> None:
    # Windows GBK console 不炸：统一以 UTF-8 写 stdout
    sys.stdout.buffer.write((text + "\n").encode("utf-8", "replace"))
    sys.stdout.buffer.flush()


def load_active_cfg() -> dict:
    raw = {}
    if CFG.is_file():
        try:
            import yaml
            raw = (yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}).get(
                "active_behavior", {})
        except Exception:
            raw = {}
    # 与 web 同口径：注入通道矩阵是唯一真相（emoji 出口/注入/生长/时间自决以矩阵为准）
    return inject_channels.overlay_active(cfgmod.merge_config(raw), inject_channels.load(CFG))


def cmd_nudge(args) -> int:
    """拼主动卡片并注入。测试工具守则：默认 dry_run 只打印；
    真的要写进她心跳文件，必须显式 --provider openclaw（绝不读线上 config 顺手翻真）。"""
    c = load_active_cfg()
    state = state_store.load(STATE)
    content = life_content.load_content(CONTENT)
    journal = life_journal.read_journal()
    provider = args.provider or "dry_run"
    card = motivation.build_motivation_card(
        state, content, journal, str(datetime.now().date()),
        emoji_mode=c.get("emoji_mode", "off"))
    res = injector.inject_motivation(card, provider=provider)
    out(f"[nudge] provider={provider} sent={res.get('sent')} "
        f"written={res.get('written', False)}")
    out("[card] ----")
    out(card)
    out("[card] ----")
    if res.get("path"):
        out(f"[written] {res['path']}")
    return 0


def cmd_sched(args) -> int:
    """E3 时间自决：列出她排的待开时刻 + inbox 原文（只读，不消费不写）。"""
    c = load_active_cfg()
    items = scheduler.pending()
    if not items:
        out("[sched] 没有待排时刻")
    else:
        for it in items:
            out(f"[sched] {it['at']} raw={it['raw']!r}")
    inbox = scheduler.read_inbox()
    if inbox.strip():
        out("[sched] inbox: ----")
        out(inbox.strip())
        out("[sched] inbox: ----")
    else:
        out("[sched] inbox 空")
    out(f"[sched] enabled={c.get('schedule_enabled')} cap={c.get('schedule_cap')}")
    return 0


def cmd_tick(args) -> int:
    """跑一次状态机 tick：先消费发送日志（__REPLY__/__SELF__/__PAUSE__/__RESUME__），再推进状态并落库。"""
    c = load_active_cfg()
    state = state_store.load(STATE)
    state, _kinds = send_feed.consume(state, c)
    if state.get("initialized"):
        nxt = state_machine.tick(state, c)
    else:
        # 首 tick 前也捡 consume 落的 paused：__PAUSE__ 在全新 state 上不丢
        init = state_store.default_state()
        init["paused"] = bool(state.get("paused"))
        nxt = state_machine.tick(init, c)
    state_store.save(nxt, STATE)
    window = state_machine.should_open_window(nxt, c)
    # 暂停（__PAUSE__）是物理通道信号：窗口照算但不拼卡不注入，报告用 PAUSED 诚实标出
    win = "PAUSED" if nxt.get("paused") else ("OPEN" if window else "close")
    out(f"[tick] energy={nxt.get('energy')} mood={nxt.get('mood')} "
        f"social_need={round(nxt.get('social_need', 0), 3)} "
        f"window={win} "
        f"paused={bool(nxt.get('paused'))} "
        f"unanswered={nxt.get('unanswered_count')}")
    return 0


def cmd_pause(args) -> int:
    """写入 __PAUSE__：链路暂停信号，心跳下次 tick 起暂停主动窗口（不拼卡不 inject）。"""
    ok = send_feed.signal(send_feed.PAUSE)
    out(f"[pause] {'已写 __PAUSE__ → 心跳下次 tick 暂停主动窗口' if ok else '写失败'}")
    return 0


def cmd_resume(args) -> int:
    """写入 __RESUME__：解除暂停，心跳下次 tick 恢复主动窗口。"""
    ok = send_feed.signal(send_feed.RESUME)
    out(f"[resume] {'已写 __RESUME__ → 心跳下次 tick 恢复主动窗口' if ok else '写失败'}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m active.cli",
        description="主动链路手动测试 CLI（web 无假身替代，测试直敲状态机内部接口）")
    sub = p.add_subparsers(dest="cmd", required=True)
    pn = sub.add_parser("nudge", help="拼主动卡片并注入（默认 dry_run，只打印）")
    pn.add_argument("--provider", choices=["dry_run", "openclaw"], default=None,
                    help="显式指定；默认 dry_run——测试绝不读线上 config 顺手翻真")
    pn.set_defaults(func=cmd_nudge)
    pt = sub.add_parser("tick", help="跑一次状态机 tick 并落库")
    pt.set_defaults(func=cmd_tick)
    ps = sub.add_parser("sched", help="E3 时间自决：列出待开时刻 + inbox 原文（只读）")
    ps.set_defaults(func=cmd_sched)
    pp = sub.add_parser("pause", help="链路暂停：心跳暂停主动窗口（写 __PAUSE__）")
    pp.set_defaults(func=cmd_pause)
    pr = sub.add_parser("resume", help="链路恢复：解除暂停（写 __RESUME__）")
    pr.set_defaults(func=cmd_resume)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
