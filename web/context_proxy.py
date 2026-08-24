"""context_proxy.py — 透明 OpenAI 兼容上下文网关（P0：meter 旁路，只观察不裁剪）。

定位（见 new/ramdump_live/爱语上下文优化_我方开销对照_2026-08-23.md §5 路A）：
把 OpenClaw 的 model provider base_url 指到这 → OpenClaw 按 OpenAI 格式发请求 →
本网关**原样**转发上游，只在转发间隙记录每轮拼装特征（按角色字符数、消息数、would_trim
估算）进 data/context_stats_proxy.jsonl，供 /api/context/stats 读。

P0 严肃铁律：对请求**一个字都不改**，裁剪(KEY_SEND_HISTORY_LIMIT 等价)是 P1 的事。
mode=meter（config.yaml context_meter.mode）时坚决不裁剪，只记 would_trim 的"如果裁会省多少"。

独立起：python -m web.context_proxy  → http://127.0.0.1:18781
model → 上游 映射在 config.yaml context_meter.upstreams。
上行头原样透传（OpenClaw 会带上它存的 provider key，代理不碰 key）。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import context_clean
from .context_meter import _resolve, load_meter_config

_LOG_LOCK = threading.Lock()


def _log_observe(cfg: dict, ev: dict) -> None:
    """把一条观察事件追加进 proxy_log（不同进程写不同文件，天然无竞争）。"""
    p = _resolve(cfg, cfg["proxy_log"])
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_LOCK, p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _role_chars(messages: list) -> dict:
    """按角色统计字符数；system 单算（恒量），其余算进 history(滚雪球的那部分)。"""
    out = {"system": 0, "history": 0}
    for m in messages:
        role = m.get("role")
        c = m.get("content")
        if isinstance(c, str):
            n = len(c)
        elif isinstance(c, list):
            n = sum(len(b.get("text") or "") for b in c if isinstance(b, dict))
        else:
            n = 0
        if role == "system":
            out["system"] += n
        else:
            out["history"] += n
    return out


def _would_trim(messages: list, keep_turns: int = 40) -> dict:
    """P0 只算不裁：估算"如果只留最近 keep_turns 轮历史会省多少字符"。

    规则（对齐爱语 KEY_SEND_HISTORY_LIMIT 精神）：system 恒保留；user/assistant/
    toolResult 按"一轮"计数（user 或带 toolCall 的 assistant 起头），超出部分算可裁字符。
    """
    if not messages:
        return {"kept": 0, "would_trim_chars": 0, "total_history": 0}
    # 简单近似：把 system 之外的按序逆推，保留最后 keep_turns 个"相邻块"，前面的都算可裁
    tails = 0
    would_trim = 0
    total_history = 0
    for m in reversed(messages):
        c = m.get("content")
        n = len(c) if isinstance(c, str) else (
            sum(len(b.get("text") or "") for b in c if isinstance(b, dict))
            if isinstance(c, list) else 0)
        total_history += n
        if tails < keep_turns:
            tails += 1
        else:
            would_trim += n
    return {"kept_turns": keep_turns, "total_history": total_history,
            "would_trim_chars": would_trim}


def create_proxy_app() -> FastAPI:
    app = FastAPI(title="小语 · 上下文网关(P0 meter)", version="0.1.0")

    @app.post("/chat/completions")
    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        cfg = load_meter_config()
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"message": "bad json"}}, status_code=400)

        model = body.get("model") or ""
        upstream = cfg.get("upstreams") or {}
        base = upstream.get(model) or upstream.get(model.split("/")[-1])
        if not base:
            _log_observe(cfg, {
                "type": "proxy_skip", "model": model,
                "reason": "upstream 未配置",
            })
            return JSONResponse({"error": {"message": f"no upstream for {model}"}},
                                status_code=502)
        url = base.rstrip("/") + "/chat/completions"

        # —— 清洗器（P1 第一刀：心跳空轮折叠）——
        # 铁律：默认 dry_run（config.clean.dry_run=True）只算账不改 body；
        # 只有显式 enabled&&!dry_run 才会在转发前替换 messages。
        clean_cfg = cfg.get("clean") or {}
        clean_stats = None
        if clean_cfg.get("enabled"):
            msgs = body.get("messages") or []
            clean_stats = context_clean.build_clean_stats(msgs)
            if not clean_cfg.get("dry_run", True):
                new_msgs, _ = context_clean.clean_messages(
                    msgs, clean_cfg.get("keep_recent_rounds", 1))
                body["messages"] = new_msgs

        # 观察：角色字符、消息数、would_trim 估算（不改任何东西）
        # 字段与 trajectory 的 context.compiled 事件同构：system_chars / history_chars
        rc = _role_chars(body.get("messages") or [])
        wt = _would_trim(body.get("messages") or [])
        obs = {
            "type": "proxy_observe",
            "ts": int(time.time() * 1000),
            "model": model,
            "stream": bool(body.get("stream")),
            "src": "proxy",
            "system_chars": rc["system"],
            "history_chars": rc["history"],
            **wt,
            "n_messages": len(body.get("messages") or []),
            "clean": clean_stats,   # None=清洗器未开; dict=该轮清洗账(dry_run 也算)
        }

        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "content-length", "connection")}
        headers["accept-encoding"] = "identity"  # 免得上游 gzip 包在透传里打架
        timeout = httpx.Timeout(600.0, connect=10.0)

        if body.get("stream"):
            async def passthrough():
                nonlocal obs
                usage_seen = None
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream("POST", url, json=body,
                                                 headers=headers) as resp:
                            obs["upstream_status"] = resp.status_code
                            async for chunk in resp.aiter_raw():
                                yield chunk
                                # 顺带扫 usage（DeepSeek 流末 chunk 带 usage，尽力而为）
                                if usage_seen is None:
                                    usage_seen = _sniff_usage(chunk)
                    obs["usage"] = usage_seen
                except httpx.HTTPError as e:
                    obs["error"] = repr(e)
                    yield b'data: {"error": ' + json.dumps(
                        repr(e), ensure_ascii=False).encode("utf-8") + b'}\n\n'
                finally:
                    _log_observe(cfg, obs)

            return StreamingResponse(
                passthrough(), media_type="text/event-stream")

        # 非流式
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=body, headers=headers)
            payload = resp.json()
            obs["upstream_status"] = resp.status_code
            u = payload.get("usage")
            obs["usage"] = u and {
                "input": u.get("prompt_tokens"),
                "output": u.get("completion_tokens"),
                "total": u.get("total_tokens"),
            }
            _log_observe(cfg, obs)
            return JSONResponse(
                content=payload,
                status_code=resp.status_code,
                headers={"content-type": "application/json"},
            )
        except httpx.HTTPError as e:
            obs["error"] = repr(e)
            _log_observe(cfg, obs)
            return JSONResponse({"error": {"message": repr(e)}}, status_code=502)

    @app.get("/models")
    @app.get("/v1/models")
    async def list_models():
        cfg = load_meter_config()
        idx = [1]
        model_ids = []
        for k in (cfg.get("upstreams") or {}):
            mm = k.split("/")[-1]
            model_ids.append({"id": mm, "object": "model",
                              "owned_by": k.split("/")[0]})
        # 让 OpenClaw 能列出它认的 id（带 provider 前缀也算上）
        for k in (cfg.get("upstreams") or {}):
            if all(m["id"] != k for m in model_ids):
                model_ids.append({"id": k, "object": "model",
                                  "owned_by": "proxy"})
        return {"object": "list", "data": model_ids}

    return app


def _sniff_usage(chunk: bytes) -> dict | None:
    """SSE chunk 里找 usage（尽力而为，找不到返回 None 不报错）。"""
    text = chunk.decode("utf-8", errors="ignore")
    if '"usage"' not in text:
        return None
    try:
        lines = [ln for ln in text.splitlines() if ln.startswith("data: ")]
        for ln in lines:
            payload = json.loads(ln[6:])
            u = payload.get("usage")
            if u:
                return {"input": u.get("prompt_tokens"),
                        "output": u.get("completion_tokens"),
                        "total": u.get("total_tokens")}
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    return None


proxy_app = create_proxy_app()

if __name__ == "__main__":
    import uvicorn
    cfg = load_meter_config()
    uvicorn.run("web.context_proxy:proxy_app", host="127.0.0.1",
                port=int(cfg.get("proxy_port", 18781)))
