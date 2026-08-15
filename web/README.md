# 小语 · Web 伴侣后台

人格调参 + 记忆可视化 + 状态查看 的伴侣台。跑在**本机**，不直接发微信（微信单一出口由 OpenClaw/ClawBot 负责）。

## 启动

```bash
cd E:/college_information/girl
# 首次需装依赖（已装可跳过）
pip install -r web/requirements.txt
python -m uvicorn web.main:app --host 127.0.0.1 --port 18780
```

打开 http://127.0.0.1:18780

> **关于端口**：默认 `18780`（落在 OpenClaw 派生端口段内，网关是 `18789`，避开 8000 这类常用占用）。想换就改命令里的 `--port`，或改 `web/main.py` 末尾。Uvicorn 冷门端口 http://127.0.0.1:18780

## 页面

- **基础设定**：小语人设（名字/关系/年龄/背景/性格/定位 → `girl_workspace/IDENTITY.md`）+ 主人资料（称呼/职业/作息/喜好 → `girl_workspace/USER.md`）+ 初始化方式开关（**微信一步步问** = 让 AI 在微信里自然地一点点了解你；**已在 Web 填好** = 照着资料认识你不反复问）。保存后 `setup.py` 渲染写入两个文件，下条消息生效。两端共用已有的「日常对话→记忆沉淀」。
- **人格调参**：5 维滑块（甜度/高冷/主动阈值/情绪波动/幽默）→ 保存后 `soul_render.py` 渲染并**重写 `girl_workspace/SOUL.md` 的滑块段**。SOUL.md 在会话启动时读取，所以**下一条微信消息生效**，无需重启。
- **主动状态机**：三环仪表实时看精力/情绪/渴望；参数滑块（开启阈值/冷却/每日上限/勿扰/深夜窗口/依恋轴/生长·注入方式）保存到 `data/config.yaml` 的 `active_behavior`。每 15 分钟心跳推进一次状态。
- **她的一天**：小语的生活底色（`data/life_content.yaml`，JSON/YAML 直接编辑）+ 生活日志预览 + 「让她今天长一条」（grow）+「现在就推（试跑）」（nudge，dry_run 不真发）。
- **记忆**：读 OpenClaw `girl` agent 的会话（`~\.openclaw\agents\girl\sessions\`），展示小语聊过的对话。
- **人格文件**：只读展示 `girl_workspace/` 下的 SOUL/AGENTS/IDENTITY/USER.md。
- **行为**：V1 遗留页（读写 `data/config.yaml` 的 `active_behavior` 旧键），新参数请用「主动状态机」页。
- **状态**：模型 / 通道 / agent 接线概览。

> **默认档「自然淡雅」**：`open_threshold=0.5`、`daily_max=2`、`quiet 02:00–05:00`、`cooldown=300s`、`attachment=secure`。不催、不吵、走得近但留有分寸。

## 文件

| 文件 | 作用 |
|---|---|
| `main.py` | FastAPI 入口 + 全部 API |
| `soul_render.py` | 滑块值 → SOUL.md 滑块段文本 |
| `setup.py` | 基础设定：人设/资料/初始化方式 → IDENTITY.md + USER.md |
| `agent_admin.py` | 读写 girl_workspace + 读 OpenClaw 会话 |
| `personality.yaml` | 滑块值持久化（运行态生成） |
| `templates/ static/` | 前端 |

## 安全说明

- API key 在 OpenClaw 配置里（`~\.openclaw\`），**不在本项目、不上传**。
- 记忆/人格 100% 本机，后台只读展示、只在调用"保存"时写 SOUL.md。
