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
