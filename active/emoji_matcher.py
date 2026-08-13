"""emoji_matcher.py — 情绪/关键词 → 表情（字符 or 图片 URL）解析层。

两个出口，全部 dry-run，不真发：
- resolve_char(emotion)  : EmoTag + Emoji Sentiment Ranking 两个本地标注数据集 → 1 个 emoji 字符
- resolve_image(keyword) : adesk / sogou 两个稳定图源 JSON 接口 → 图片 URL
数据文件在 data/emoji/（gitignored 第三方数据集，本地自用；缺失优雅降级）。
单一出口：本模块不直发任何消息。
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
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


def resolve_char(emotion: str) -> str:
    """在 EmoTag 里按情绪分排序取榜首；同分用 ESR 极性 tie-break；缺失回退兜底。只回 1 个。"""
    cand = [r for r in _emotag() if r["score"].get(emotion)]
    if not cand:
        return _FALLBACK.get(emotion, "")
    cand.sort(key=lambda r: r["score"][emotion], reverse=True)
    top = cand[0]["score"][emotion]
    esr = _esr()
    is_pos = emotion in POSITIVE
    for r in cand:
        if r["score"][emotion] < top - 1e-9:
            break                          # 只在前一档里挑，保持情绪纯度
        p = esr.get(r["char"])
        if p is None or ((p["pos"] > p["neg"]) == is_pos):
            return r["char"]
    return cand[0]["char"]


# 稳定 JSON 图源：(provider, base_url, 固定查询参数, headers)
SOURCES = {
    "adesk": ("adesk", "https://so.picasso.adesk.com/emoji/v1/resource",
              "from=select&limit=6&order=new",
              {"Referer": "http://emoji.adesk.com/"}),
    "sogou": ("sogou", "https://image.sogou.com/napi/wap/pic",
              "start=0&len=6",
              {"User-Agent": "Mozilla/5.0"}),
}


def _http_get_json(url: str, headers: dict, timeout: float = 12.0) -> dict | None:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _http_get_bytes(url: str, headers: dict, timeout: float = 12.0) -> bytes | None:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _extract(data: dict | None, provider: str) -> str | None:
    if not data:
        return None
    if provider == "adesk":
        items = (data.get("res") or {}).get("data") or []
        if items:
            for k in ("big_url", "static_url", "url"):
                if items[0].get(k):
                    return items[0][k]
    elif provider == "sogou":
        items = (data.get("data") or {}).get("items") or []
        if items:
            return items[0].get("picUrl") or items[0].get("oriPicUrl")
    return None


def resolve_image(keyword: str, sources: list[str] | None = None,
                  timeout: float = 12.0) -> dict | None:
    """按关键词在稳定图源里抓一张图的 URL；返回 {"url","provider"}，全挂返回 None。"""
    for name in sources or ["adesk", "sogou"]:
        spec = SOURCES.get(name)
        if not spec:
            continue
        _, base, params, headers = spec
        url = f"{base}?{params}&keyword={urllib.parse.quote(keyword)}"
        img = _extract(_http_get_json(url, headers, timeout), name)
        if img:
            return {"url": img, "provider": name}
    return None


_IMG_EXT = re.compile(r"\.(png|jpe?g|gif|webp)(?:\?|$)", re.I)


def resolve_image_file(keyword: str, out_dir: str, sources: list[str] | None = None,
                       timeout: float = 12.0) -> str | None:
    """解析稳定图源→下载一张表情图到 out_dir，返回本地绝对路径；任一环节失败返回 None。"""
    hit = resolve_image(keyword, sources, timeout)
    if not hit:
        return None
    data = _http_get_bytes(hit["url"], {"User-Agent": "Mozilla/5.0"}, timeout)
    if not data:
        return None
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    m = _IMG_EXT.search(hit["url"] or "")
    ext = m.group(1).lower().replace("jpeg", "jpg") if m else "jpg"
    base = int(time.time())
    f = folder / f"meme_{base}.{ext}"
    counter = 1
    while f.exists():                       # 同秒冲突兜底
        f = folder / f"meme_{base}_{counter}.{ext}"
        counter += 1
    f.write_bytes(data)
    return str(f.resolve())
