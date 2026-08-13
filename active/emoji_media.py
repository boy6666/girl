"""emoji_media.py — 表情包图片的本地落地与清理。

职责：把 stable 图源解析到的一张表情图下载进本地「表情包文件夹」，
并周期清理过期图。单一出口：本模块只写本地文件，绝不直发微信；
girl 拿到卡里的本地路径后由 OpenClaw 的 message(action=send) 真发。
"""
from __future__ import annotations
import time
from pathlib import Path

from . import config as cfgmod, emoji_matcher


def ensure_media_dir(cfg: dict) -> Path:
    folder = Path(cfg.get("emoji_media_dir", "data/media"))
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()


def cleanup_old_media(cfg: dict, now: float | None = None) -> int:
    """删除超出 ttl 的 meme_* 旧图，返回清掉的文件数。"""
    now = now or time.time()
    ttl = float(cfg.get("emoji_media_ttl_days", 14)) * 86400
    folder = ensure_media_dir(cfg)
    removed = 0
    for f in folder.glob("meme_*"):
        try:
            if now - f.stat().st_mtime > ttl:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def resolve_to_local(keyword: str, cfg: dict | None = None) -> tuple[str | None, str | None]:
    """解析并下载一张表情图到本地文件夹。返回 (本地路径|None, provider|None)。"""
    cfg = cfg if cfg is not None else cfgmod.load_config()
    folder = ensure_media_dir(cfg)
    sources = cfg.get("emoji_sources") or ["adesk", "sogou"]
    path = emoji_matcher.resolve_image_file(keyword, str(folder), sources=sources)
    if path is None:
        return None, None
    return path, None
