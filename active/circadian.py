"""circadian.py — 她的作息：一个有自己节奏的生活逻辑，可由当天忙碌与相处双向漂移。

尊重社科：亲近之人的节奏会拽着她的作息走（social zeitgeber），但她不是被谁命令的钟，
自己今天多做几件真实的事也会自然累、想早睡。所以这里有**三层驱动**，都由真实素材喂养：

- **内驱·早**：`own_load`（今天她真实做了多少件事，来自她的生活底色）→ 自然累、就寝前移。
- **外驱·晚**：`last_contact_clock`（最近一次真实互动的时钟点，来自她的会话）落在深夜带
  → 陪他晚睡，就寝/起床同量后延（总睡眠时长不变）。
- **外驱·早**：`wind_down`（他刚说"累了/要早睡"的真话）→ 顺着早点收，就寝/起床同量前移。

同一夜晚睡优先（你们真实还在一起时，陪他）。晚/早都没有 → 按点睡。
纯函数、可测、零副作用。
"""
from . import life_sim

MIN = 60


def parse_hhmm(s: str, fallback: str = "23:00") -> tuple[int, int]:
    try:
        hh, mm = str(s).strip().split(":")
        return int(hh), int(mm)
    except (ValueError, AttributeError):
        hh, mm = fallback.split(":")
        return int(hh), int(mm)


def _m(hh: int, mm: int) -> int:
    return hh * 60 + mm


def _hhmm(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def in_band(clock_min: int, start_min: int, end_min: int) -> bool:
    """clock 是否落在 [start, end)，支持跨午夜（start>end）。"""
    if start_min <= end_min:
        return start_min <= clock_min < end_min
    return clock_min >= start_min or clock_min < end_min


def minutes_past(clock_min: int, anchor_min: int) -> int:
    """clock 相对 anchor 过了多少分钟（跨午夜感知）。"""
    return (clock_min - anchor_min) % 1440


def is_wind_down(text: str | None) -> bool:
    """他是不是真说要早睡了（早睡信号）。只认真实语句，不猜。"""
    if not text:
        return False
    keys = ("要睡了", "该睡了", "睡觉了", "先睡了", "晚安", "睡了",
            "想睡觉", "早点睡", "早睡", "很累", "好累", "太累了",
            "顶不住", "困了", "撑不住", "我真睡了")
    return any(k in text for k in keys)


def own_load(content: dict, day: str) -> int:
    """她今天真实做了几件事（生活底色里有真素材的时段数）。内驱早睡的原料。"""
    return len(life_sim.today_highlights(content, day, 23))


def _early_shift(bed0m: int, early_bedtime: str, own_load: int,
                 own_load_min_per_item: int, wind_down: bool, cc_cfg: dict) -> int:
    """就寝可前移的分钟数（内驱 + 外驱·早，封顶到 early_bedtime）。"""
    early_cap = bed0m - _m(*parse_hhmm(early_bedtime))
    early = min(own_load * own_load_min_per_item, early_cap)
    if wind_down:
        early = max(early, early_cap)   # 他说累/早睡 → 直接到最早就寝点
    return max(0, early)


def _late_shift(bed0m: int, last_contact_clock: int | None,
                late_band_end: str, max_shift_min: int) -> int:
    """就寝可后延的分钟数（外驱·晚），封顶 max_shift_min。"""
    if last_contact_clock is None:
        return 0
    band_end = _m(*parse_hhmm(late_band_end))
    if not in_band(last_contact_clock, bed0m, band_end):
        return 0
    return min(minutes_past(last_contact_clock, bed0m), max_shift_min)


def schedule(base_bedtime: str, base_wake: str, *,
             own_load: int = 0,
             last_contact_clock: int | None = None,
             wind_down: bool = False,
             early_bedtime: str = "21:00",
             late_band_end: str = "03:00",
             max_shift_min: int = 240,
             own_load_min_per_item: int = 20) -> dict:
    """把三层驱动折算成今晚就寝/明早起床。返回 {bedtime, wake, shift_min, note}。"""
    bed0m = _m(*parse_hhmm(base_bedtime))
    wake0m = _m(*parse_hhmm(base_wake))

    late = _late_shift(bed0m, last_contact_clock, late_band_end, max_shift_min)
    early = _early_shift(bed0m, early_bedtime, own_load,
                         own_load_min_per_item, wind_down, {})

    if late > 0:
        return {"bedtime": _hhmm(bed0m + late), "wake": _hhmm(wake0m + late),
                "shift_min": late, "note": "陪他晚睡"}
    if early > 0:
        return {"bedtime": _hhmm(bed0m - early), "wake": _hhmm(wake0m - early),
                "shift_min": -early, "note": "今天忙/他早睡，提前收"}
    return {"bedtime": _hhmm(bed0m), "wake": _hhmm(wake0m),
            "shift_min": 0, "note": "按点"}
