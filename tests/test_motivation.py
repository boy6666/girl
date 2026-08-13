from datetime import datetime
from active import motivation as mo

STATE = {"energy": 80.0, "mood": 0.2, "social_need": 0.7,
         "today_active_count": 0, "unanswered_count": 0}


def _filled_content():
    return {"habits": [], "favorites": {}, "schedule": {"wake": 7},
            "buckets": {"morning": ["今天遇到一只猫"], "work": [],
                        "afternoon": [], "evening": []}}


def test_card_has_all_sections_with_filled_content():
    card = mo.build_motivation_card(STATE, _filled_content(), "今天散步遇到一只猫。\n",
                                    "2026-08-11", datetime(2026, 8, 11, 9, 0))
    assert "【现在】" in card
    assert "【今天】" in card
    assert "【状态】" in card
    assert "猫" in card


def test_card_graceful_when_no_content():
    empty = {"habits": [], "favorites": {}, "schedule": {"wake": 7},
             "buckets": {"morning": [], "work": [], "afternoon": [], "evening": []}}
    card = mo.build_motivation_card(STATE, empty, "", "2026-08-11",
                                    datetime(2026, 8, 11, 9, 0))
    assert "【现在】" in card      # 中性留白
    assert "【状态】" in card
    # 无高光/无梦/无昨日 → 不给【今天】【梦】段（不硬造）
    assert "【今天】" not in card
    assert "【梦】" not in card


from active.motivation import build_motivation_card  # noqa: E402


def test_card_default_off_has_no_emoji_line():
    state = {"energy": 80, "mood": 0.6}
    card = build_motivation_card(state, {}, "", "2026-08-12")
    assert "【表情】" not in card


def test_card_char_mode_appends_emoji_line():
    state = {"energy": 80, "mood": 0.6}
    card = build_motivation_card(state, {}, "", "2026-08-12", emoji_mode="char")
    assert "【表情】" in card


def test_card_image_mode_appends_local_image_path():
    state = {"energy": 80, "mood": 0.6}
    card = build_motivation_card(state, {}, "", "2026-08-13", emoji_mode="image",
                                 emoji_resolver=lambda kw: ("C:/media/meme_1.jpg", None))
    assert "【表情】图=C:/media/meme_1.jpg" in card
    assert "message(action=send" in card


def test_card_image_mode_omits_line_when_download_fails():
    state = {"energy": 80, "mood": 0.6}
    card = build_motivation_card(state, {}, "", "2026-08-13", emoji_mode="image",
                                 emoji_resolver=lambda kw: (None, None))
    assert "【表情】" not in card
