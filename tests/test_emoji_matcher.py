# tests/test_emoji_matcher.py
import active.emoji_matcher as em


def test_emotions_are_the_8_emotag_labels():
    assert set(em.EMOTIONS) == {"anger", "anticipation", "disgust", "fear",
                                "joy", "sadness", "surprise", "trust"}


def test_emotion_from_keyword_maps_chinese():
    assert em.emotion_from_keyword("开心") == "joy"
    assert em.emotion_from_keyword("难过") == "sadness"
    assert em.emotion_from_keyword("愤怒") == "anger"


def test_emotion_from_keyword_unknown_returns_none():
    assert em.emotion_from_keyword("随便说什么") is None
    assert em.emotion_from_keyword("") is None


def test_mood_to_emotion_bands():
    assert em.mood_to_emotion(-0.5, 80) == "sadness"
    assert em.mood_to_emotion(0.6, 80) == "joy"
    assert em.mood_to_emotion(0.0, 80) is None
    assert em.mood_to_emotion(None, 80) is None


def test_mood_to_emotion_too_tired_returns_none():
    assert em.mood_to_emotion(0.6, 20) is None  # 太累不配表情


def test_resolve_char_sadness_top_is_crying(monkeypatch, tmp_path):
    em.EMOTAG_CSV = tmp_path / "no.csv"          # 数据集缺失 → 兜底
    em._emotag.cache_clear()
    assert em.resolve_char("sadness") == em._FALLBACK["sadness"]


def test_resolve_char_unknown_emotion_returns_empty():
    assert em.resolve_char("not-a-real-emotion") == ""


def _fake_adesk(url, headers, timeout):
    return {"res": {"data": [{"big_url": "https://img/ade.png", "url": "https://img/ade.png"}]}}


def test_resolve_image_adesk_first(monkeypatch):
    monkeypatch.setattr(em, "_http_get_json", _fake_adesk)
    out = em.resolve_image("开心")
    assert out == {"url": "https://img/ade.png", "provider": "adesk"}


def test_resolve_image_falls_back_to_sogou(monkeypatch):
    calls = {}

    def fake(url, headers, timeout):
        calls["n"] = calls.get("n", 0) + 1
        if calls["n"] == 1:
            return None            # adesk 挂
        return {"data": {"items": [{"picUrl": "https://img/sg.png"}]}}

    monkeypatch.setattr(em, "_http_get_json", fake)
    out = em.resolve_image("开心")
    assert out == {"url": "https://img/sg.png", "provider": "sogou"}


def test_resolve_image_all_down_returns_none(monkeypatch):
    monkeypatch.setattr(em, "_http_get_json", lambda *a, **k: None)
    assert em.resolve_image("开心") is None


def test_resolve_image_file_downloads_and_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "_http_get_json", _fake_adesk)          # 复用既有的 fake 返回 URL
    monkeypatch.setattr(em, "_http_get_bytes",
                        lambda url, headers, timeout: b"\x89PNG-fake-bytes")
    p = em.resolve_image_file("开心", str(tmp_path))
    assert p is not None and p.startswith(str(tmp_path))
    written = list(tmp_path.iterdir())
    assert len(written) == 1 and written[0].read_bytes() == b"\x89PNG-fake-bytes"

def test_resolve_image_file_none_when_download_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "_http_get_json", _fake_adesk)
    monkeypatch.setattr(em, "_http_get_bytes", lambda url, headers, timeout: None)
    assert em.resolve_image_file("开心", str(tmp_path)) is None
    assert list(tmp_path.iterdir()) == []            # 不落任何文件

def test_resolve_image_file_none_when_no_source(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "_http_get_json", lambda url, headers, timeout: None)
    assert em.resolve_image_file("开心", str(tmp_path)) is None
