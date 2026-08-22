"""inject_channels.py — 注入通道总控（爱语 KEY_INJECT_* 惰性注入 10 开关移植）。

2026-08-21 grill 拍板：config.yaml 顶层 `inject_channels` 段 = 唯一真相，
10 条通道各带 {enabled, provider}，全量可读写，Web「注入通道总控」一个页面管完。
Python 侧各通道的 enabled/provider 一律以它为准（不再散在各段里）；
通道**特有参数**（reflection.window / growth.interval_days / emoji_sources…）
仍在各自段里，不受矩阵影响。

status 判定：
  live  = 该通道启用且 provider 接真（momentum→openclaw）
  trial = 启用但 provider=dry_run / 未接真（只试跑不真写）
  off   = 通道关闭
"""
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "config.yaml"

# 每条 {enabled, provider} —— 默认值对齐 2015 拆矩阵前的线上有效值
DEFAULTS = {
    "motivation": {"enabled": True,  "provider": "openclaw"},  # 主动找话（动机卡→heartbeat.md）
    "reflection": {"enabled": True,  "provider": "openclaw"},  # 每晚自我反思（reflect.md）
    "diary":      {"enabled": True,  "provider": "openclaw"},  # 每晚日记（diary_in.md）
    "dream":      {"enabled": True,  "provider": "dry_run"},   # 非每日梦记（dream_in.md）
    "growth":     {"enabled": True,  "provider": "openclaw"},  # 持续生长（GROWTH.md 底子续长）
    "schedule":   {"enabled": True,  "provider": "openclaw"},  # E3 时间自决（「下次几点」）
    "emoji":      {"enabled": True,  "provider": "image"},     # 图片表情包：off|image（char 已废弃）
    "relation":   {"enabled": True,  "provider": "openclaw"},  # 羁绊/依恋线索（寄卡片，OpenClaw 侧执行）
    "perception": {"enabled": False, "provider": "none"},      # 感知注记：none=零成本 note / vision=多模态描述
    "search":     {"enabled": True,  "provider": "openclaw"},  # 记忆检索闸（镜像 OpenClaw QMD，契约型）
}

META = {
    "motivation": {"label": "主动找话",  "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "心跳开窗时",
                   "detail": "动机卡→heartbeat.md，说不说由她"},
    "reflection": {"label": "每晚反思",  "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "每晚 window 时",
                   "detail": "反思卡→reflect.md，产物进记忆，不发消息"},
    "diary":      {"label": "每晚日记",  "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "每晚该寝时",
                   "detail": "日记卡→diary_in.md，第一人称叙事"},
    "dream":      {"label": "非每日梦记", "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "起床忆昨夜之梦",
                   "detail": "真实日间残余做由头，非梦夜不造假"},
    "growth":     {"label": "持续生长",  "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "每 interval_days",
                   "detail": "有真实沉淀才续长 GROWTH.md，没长不催"},
    "schedule":   {"label": "时间自决",  "providers": ["dry_run", "openclaw"],
                   "side": "python", "run": "每次开窗",
                   "detail": "E3「下次几点」追问 + schedule_in.md 到点开窗"},
    "emoji":      {"label": "表情包",  "providers": ["off", "image"],
                   "side": "python", "run": "卡片拼表情时",
                   "detail": "image=图片表情包→【表情】图=本地路径，girl 用 message(action=send,path) 发；off=纯文字。char(字符表情)已废弃——消息文字禁 emoji 字符，颜文字可"},
    "relation":   {"label": "羁绊线索",  "providers": ["dry_run", "openclaw"],
                   "side": "contract", "run": "OpenClaw 侧",
                   "detail": "羁绊/依恋写进卡片语境，执行在 OpenClaw；记录意图"},
    "perception": {"label": "感知注记",  "providers": ["none", "vision"],
                   "side": "contract", "run": "收到图/表情/拍一拍时",
                   "detail": "none=零成本注记；vision=多模态 LLM 描述后注入"},
    "search":     {"label": "记忆检索",  "providers": ["dry_run", "openclaw"],
                   "side": "contract", "run": "OpenClaw QMD 镜像",
                   "detail": "记忆检索闸；OpenClaw 侧执行"},
}


def _read_root(path: Path) -> dict:
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load(cfg_path: Path = CONFIG_PATH) -> dict:
    """读 config.yaml 顶层 inject_channels 段并 merge 默认；缺文件/异常→纯默认。"""
    raw = _read_root(cfg_path).get("inject_channels") or {}
    out = {}
    for name, dflt in DEFAULTS.items():
        seg = dict(dflt)
        if isinstance(raw.get(name), dict):
            for k in ("enabled", "provider"):
                if k in raw[name]:
                    seg[k] = raw[name][k]
        out[name] = seg
    return out


def save(channels: dict, cfg_path: Path = CONFIG_PATH) -> dict:
    """把整份矩阵写回 config.yaml（合并：不碰其它段）。返回写后的矩阵。"""
    data = _read_root(cfg_path)
    clean = {}
    for name in DEFAULTS:
        seg = channels.get(name)
        if isinstance(seg, dict):
            clean[name] = {
                "enabled": bool(seg.get("enabled", DEFAULTS[name]["enabled"])),
                "provider": str(seg.get("provider", DEFAULTS[name]["provider"])) or DEFAULTS[name]["provider"],
            }
    data["inject_channels"] = clean
    import yaml
    cfg_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    return load(cfg_path)


def update(name: str, cfg_path: Path = CONFIG_PATH, **kw) -> dict:
    """单通道改：读→改该条→写回。返回整份矩阵（调用方拿最新状态）。"""
    channels = load(cfg_path)
    if name not in DEFAULTS:
        return channels
    seg = channels[name]
    for k, v in kw.items():
        if k in ("enabled", "provider") and v is not None:
            seg[k] = v
    return save(channels, cfg_path)


def on(channels: dict, name: str) -> bool:
    seg = channels.get(name)
    return bool(seg and seg.get("enabled"))


def provider(channels: dict, name: str) -> str:
    seg = channels.get(name)
    return (seg or {}).get("provider", DEFAULTS[name]["provider"])


def overlay_active(c: dict, channels: dict | None = None) -> dict:
    """把矩阵里由 Python 侧消费的通道键覆盖进配置参数带，让 `_active_cfg`/CLI 以矩阵为准。"""
    channels = channels or load()
    live = {k: c[k] for k in c}                    # 浅拷贝
    live["inject_provider"] = provider(channels, "motivation")
    live["grow_provider"] = provider(channels, "growth")
    live["emoji_mode"] = provider(channels, "emoji")
    live["schedule_enabled"] = on(channels, "schedule")
    return live


def status(channels: dict, name: str) -> str:
    seg = channels.get(name)
    if not seg or not seg.get("enabled"):
        return "off"
    if seg.get("provider") in ("openclaw", "vision"):
        return "live"
    return "trial"
