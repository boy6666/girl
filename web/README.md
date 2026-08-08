# 小语 · Web 伴侣后台

人格调参 + 记忆可视化 + 状态查看 的伴侣台。跑在**本机**，不直接发微信（微信单一出口由 OpenClaw/ClawBot 负责）。

## 启动

```bash
cd E:/college_information/girl
# 首次需装依赖（已装可跳过）
pip install -r web/requirements.txt
python -m uvicorn web.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000

## 页面

- **人格调参**：5 维滑块（甜度/高冷/主动阈值/情绪波动/幽默）→ 保存后 `soul_render.py` 渲染并**重写 `girl_workspace/SOUL.md` 的滑块段**。SOUL.md 在会话启动时读取，所以**下一条微信消息生效**，无需重启。
- **记忆**：读 OpenClaw `girl` agent 的会话（`~\.openclaw\agents\girl\sessions\`），展示小语聊过的对话。
- **人格文件**：只读展示 `girl_workspace/` 下的 SOUL/AGENTS/IDENTITY/USER.md。
- **行为**：读写 `data/config.yaml` 的 `active_behavior`（V1 定时主动的基础；V1.5 状态机接管 energy/mood/social_need）。
- **状态**：模型 / 通道 / agent 接线概览。

## 文件

| 文件 | 作用 |
|---|---|
| `main.py` | FastAPI 入口 + 全部 API |
| `soul_render.py` | 滑块值 → SOUL.md 滑块段文本 |
| `agent_admin.py` | 读写 girl_workspace + 读 OpenClaw 会话 |
| `personality.yaml` | 滑块值持久化（运行态生成） |
| `templates/ static/` | 前端 |

## 安全说明

- API key 在 OpenClaw 配置里（`~\.openclaw\`），**不在本项目、不上传**。
- 记忆/人格 100% 本机，后台只读展示、只在调用"保存"时写 SOUL.md。
