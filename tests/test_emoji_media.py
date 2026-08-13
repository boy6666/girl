# tests/test_emoji_media.py
import os
import time
from pathlib import Path
import active.emoji_media as ep


def _cfg(tmp_path, ttl=14):
    return {"emoji_media_dir": str(tmp_path / "media"),
            "emoji_media_ttl_days": ttl,
            "emoji_sources": ["adesk", "sogou"]}


def test_ensure_media_dir_creates_and_returns_abs(tmp_path):
    d = ep.ensure_media_dir(_cfg(tmp_path))
    assert d.is_dir()
    assert str(d).startswith(str(tmp_path))


def test_cleanup_removes_old_keeps_fresh(tmp_path):
    d = Path(tmp_path) / "media"
    d.mkdir(parents=True)
    old, fresh = d / "meme_1.jpg", d / "meme_2.jpg"
    old.touch(); fresh.touch()
    now = time.time()
    os.utime(old, (now - 15 * 86400, now - 15 * 86400))   # 15 天前 → 过期
    os.utime(fresh, (now - 1000, now - 1000))              # 新鲜
    removed = ep.cleanup_old_media(_cfg(tmp_path), now=now)
    assert removed == 1
    assert fresh.exists() and not old.exists()


def test_resolve_to_local_returns_path_on_success(monkeypatch, tmp_path):
    monkeypatch.setattr(ep.emoji_matcher, "resolve_image_file",
                        lambda kw, od, sources=None, timeout=12.0: str(Path(od) / "x.jpg"))
    local, _ = ep.resolve_to_local("开心", _cfg(tmp_path))
    assert local is not None and local.endswith("x.jpg")


def test_resolve_to_local_returns_none_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(ep.emoji_matcher, "resolve_image_file",
                        lambda kw, od, sources=None, timeout=12.0: None)
    assert ep.resolve_to_local("开心", _cfg(tmp_path)) == (None, None)
