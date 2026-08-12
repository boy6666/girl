"""emoji_matcher.py — 情绪/关键词 → 表情（字符 or 图片 URL）解析层。

两个出口，全部 dry-run，不真发：
- resolve_char(emotion)  : EmoTag + Emoji Sentiment Ranking 两个本地标注数据集 → 1 个 emoji 字符
- resolve_image(keyword) : adesk / sogou 两个稳定图源 JSON 接口 → 图片 URL
数据文件在 data/emoji/（gitignored 第三方数据集，本地自用；缺失优雅降级）。
单一出口：本模块不直发任何消息。
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "emoji"
EMOTAG_CSV = DATA / "EmoTag1200-scores.csv"
ESR_TSV = DATA / "emoji_sentiment_ranking.tsv"

# 8 个离散情绪（EmoTag 的 8 列），本模块唯一的规范情绪空间
EMOTIONS = ["anger", "anticipation", "disgust", "fear",
            "joy", "sadness", "surprise", "trust"]
POSITIVE = {"anticipation", "joy", "surprise", "trust"}
NEGATIVE = {"anger", "disgust", "fear", "sadness"}

# 中文口语词 → 规范情绪（8 个 EmoTag 情绪之一）
EMOTION_SYNONYMS = {
    "开心": "joy", "高兴": "joy", "快乐": "joy", "愉快": "joy", "哈哈": "joy",
    "难过": "sadness", "伤心": "sadness", "悲伤": "sadness", "哭": "sadness",
    "委屈": "sadness", "失落": "sadness",
    "生气": "anger", "愤怒": "anger", "气": "anger", "不爽": "anger",
    "害怕": "fear", "恐惧": "fear", "怕": "fear", "紧张": "fear",
    "惊讶": "surprise", "吃惊": "surprise", "哇": "surprise",
    "期待": "anticipation", "盼望": "anticipation", "憧憬": "anticipation",
    "安心": "trust", "信任": "trust", "踏实": "trust", "爱": "trust",
    "讨厌": "disgust", "恶心": "disgust", "嫌": "disgust",
}

# 兜底表：数据集缺失/未匹配时也能给出合理字符（本地无条件可用）
_FALLBACK = {
    "anger": "😠", "anticipation": "🤞", "disgust": "🤢", "fear": "😨",
    "joy": "😄", "sadness": "😢", "surprise": "😲", "trust": "😊",
}


@lru_cache(maxsize=None)
def _emotag() -> list[dict]:
    """EmoTag：150 表情 × 8 情绪分。文件缺失 → []。"""
    rows = []
    if not EMOTAG_CSV.is_file():
        return rows
    with EMOTAG_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                score = {e: float(r[e]) for e in EMOTIONS}
            except (ValueError, KeyError):
                continue
            rows.append({"char": r["emoji"], "name": r["name"], "score": score})
    return rows


@lru_cache(maxsize=None)
def _esr() -> dict:
    """Emoji Sentiment Ranking：char → {pos, neg} 极性，给同分候选做 tie-break。"""
    m = {}
    if not ESR_TSV.is_file():
        return m
    with ESR_TSV.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            ch, neg, _, pos = p[0], p[1], p[2], p[3]
            try:
                m[ch] = {"pos": float(pos), "neg": float(neg)}
            except ValueError:
                continue
    return m


def emotion_from_keyword(word: str | None) -> str | None:
    """中文口语词 → 规范情绪。未匹配返回 None。"""
    if not word:
        return None
    return EMOTION_SYNONYMS.get(word.strip())


def mood_to_emotion(mood: float | None, energy: float | None = None) -> str | None:
    """状态机 mood(-1..1)/energy(0..100) → 情绪。情绪中性或太累 → None（不配表情）。"""
    if mood is None:
        return None
    if energy is not None and energy < 35:
        return None
    if mood < -0.2:
        return "sadness"
    if mood > 0.3:
        return "joy"
    return None
