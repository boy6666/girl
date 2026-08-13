"""test_fresh_boot.py — 放在另一台干净机器上能否直接跑起来？

模拟「无 OpenClaw、无 data/config.yaml、无 state.json、无 girl_workspace/memory」的
全新环境：把 web.main 用到的所有运行时路径指到不存在的空目录后冷启动 TestClient，
断言首页与全部读侧端点都返回 200，不崩、不写入 OpenClaw、默认 dry_run（零发送）。
"""
from fastapi.testclient import TestClient


def test_boots_clean_without_openclaw_or_data(monkeypatch, tmp_path):
    # —— 把整台机器"清空"：OpenClaw 会话 / 数据 / 记忆目录都不存在 ——
    fake_openclaw = tmp_path / "no_openclaw" / "agents" / "girl" / "sessions"
    ws_empty = tmp_path / "ws_empty"                 # 空 girl_workspace
    no_cfg = tmp_path / "empty" / "config.yaml"      # 无 config
    no_state = tmp_path / "empty" / "state.json"     # 无 state

    from web import agent_admin, active_bridge
    from active import reflection, diary, dream

    monkeypatch.setattr(agent_admin, "SESSIONS_DIR", fake_openclaw)
    monkeypatch.setattr(agent_admin, "WORKSPACE", ws_empty)
    monkeypatch.setattr(active_bridge, "CFG", no_cfg)
    monkeypatch.setattr(active_bridge, "STATE", no_state)
    monkeypatch.setattr(active_bridge, "CONTENT", no_cfg)

    monkeypatch.setattr(reflection, "REFLECT_INTAKE", tmp_path / "reflect_in.md")
    monkeypatch.setattr(reflection, "REFLECTIONS_DIR", tmp_path / "reflections")
    monkeypatch.setattr(diary, "DIARY_INTAKE", tmp_path / "diary_in.md")
    monkeypatch.setattr(diary, "DIARY_DIR", tmp_path / "diary")
    monkeypatch.setattr(dream, "DREAM_INTAKE", tmp_path / "dream_in.md")
    monkeypatch.setattr(dream, "DREAMS_DIR", tmp_path / "dreams")

    from web.main import app
    with TestClient(app) as c:
        assert c.get("/").status_code == 200                                              # 首页
        for path in ("/api/status", "/api/active/state", "/api/active/life",
                     "/api/active/circadian", "/api/active/reflection",
                     "/api/active/diary", "/api/active/dream"):
            r = c.get(path)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"

        # 无会话 → latest None → 作息是基础值，不崩、不造假
        circ = c.get("/api/active/circadian").json()
        assert circ["inputs"]["last_contact_clock"] is None
        assert circ["schedule"]["bedtime"]  # 有基础就寝时间

        # 无 config → 全部回落 dry_run（零发送保障）
        d = c.get("/api/active/diary").json()
        assert d["status"]["live"] is False or d["config"]["provider"] == "dry_run"
