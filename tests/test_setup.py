"""test_setup.py — 基础设定：人设/资料渲染 + 初始化方式"""
from pathlib import Path

import yaml

from web import setup as s


def _cfg(tmp_path: Path) -> Path:
    # 模拟已有人格/主动块，验证保存不丢其他段
    p = tmp_path / "config.yaml"
    p.write_text(
        "personality:\n  sweetness: 65\nactive_behavior:\n  daily_max: 2\n",
        encoding="utf-8",
    )
    return p


def test_load_defaults_when_unset(tmp_path):
    d = s.load(_cfg(tmp_path))
    assert d["init_mode"] == "web_fill"
    assert d["girl"]["name"] == "小语"
    assert d["owner"]["nickname"] == ""


def test_save_persists_and_preserves_other_sections(tmp_path):
    cfg = _cfg(tmp_path)
    d = s.save(cfg, {
        "init_mode": "wechat_ask",
        "girl": {"name": "小语", "age": "24"},
        "owner": {"job": "程序员"},
    })
    assert d["init_mode"] == "wechat_ask"
    assert d["girl"]["age"] == "24"
    assert d["owner"]["job"] == "程序员"
    # 其他段不丢
    raw = cfg.read_text(encoding="utf-8")
    assert "sweetness: 65" in raw and "daily_max: 2" in raw


def test_save_renders_identity_and_user(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    ws = tmp_path / "girl_workspace"
    monkeypatch.setattr(s, "WORKSPACE", ws)
    ws.mkdir(parents=True, exist_ok=True)
    s.save(cfg, {
        "init_mode": "web_fill",
        "girl": {"name": "小语", "age": "24", "birthday": "3月7日"},
        "owner": {"nickname": "叫我", "job": "程序员", "interests": "打游戏"},
    })
    ident = (ws / "IDENTITY.md").read_text(encoding="utf-8")
    user = (ws / "USER.md").read_text(encoding="utf-8")
    assert "**名字**：小语" in ident and "生日：3月7日" in ident
    assert "**职业**：程序员" in user and "**兴趣爱好**：打游戏" in user


def test_init_mode_wechat_ask_injects_question_guidance(tmp_path):
    u = s.render_user({"nickname": ""}, "wechat_ask")
    assert "微信一步步问" in u
    assert "自然地" in u


def test_render_user_blank_owner_is_honest_not_empty(tmp_path):
    u = s.render_user({}, "web_fill")
    assert "还没在后台填写资料" in u
