# 小语 · AI 女友

一个**人格化、有终身记忆、会主动找你**的虚拟女友。你通过**微信**跟她聊天，通过 **Web 伴侣后台**调参、看她的状态与生活。记忆、人格、生活全部**本地化**，不依赖自研对话引擎。

> 详细决策地基见 `docs/VISION.md`（非 git 跟踪）。

---

## 架构（C 混合：OpenClaw 宿主 + 自研状态机）

```
┌────────────┐   ClawBot    ┌──────────────────────────┐
│   微信     │ ◄──────────► │     OpenClaw Gateway     │
│  (用户)    │              │   ┌──────────────────┐    │
└────────────┘              │   │  [girl agent]    │    │   ← 她的"声音"
                            │   │  SOUL.md 人格      │    │
                            │   │  AGENTS.md 规则    │    │
                            │   │  session/QMD 记忆  │    │
                            │   └─────────┬─────────┘    │
                            └─────────────┼──────────────┘
                                          │ 读状态/写人格/注入卡片
                            ┌─────────────▼──────────────┐
                            │  Python —— active/ 状态机    │   ← 她的"内在"
                            │  energy/mood/social_need    │
                            │  + 生活模拟(她的一天/日志)    │
                            │  + 心跳循环 + /api/active/*  │
                            └─────────────┬──────────────┘
                                          │
                            ┌─────────────▼──────────────┐
                            │  Web 伴侣后台 (FastAPI)      │   ← 你的"遥控器"
                            │  人格滑块/记忆/主动状态机/她的一天 │
                            └────────────────────────────┘
```

**单一出口（铁律）**：微信消息只由 OpenClaw 统一发送。Python 后端**永不直接发微信**——它只把「动机卡片」写进 girl agent 的心跳摄入文件，由小语用自己的声音决定说不说、说什么，再由 OpenClaw 发出去。

---

## 技术栈

- **OpenClaw**（2026.7.1-2）：大脑宿主、girl agent、微信（ClawBot）通道、记忆
- **Python 3.11+**：`active/` 状态机 + 生活模拟（FastAPI、PyYAML、pytest）
- **Web**：FastAPI + Jinja2 + 原生 JS/CSS

---

## 当前能力

| 模块 | 能力 |
|---|---|
| **人格** | 5 维滑块 → 重写 `girl_workspace/SOUL.md`，下条消息生效 |
| **主动状态机（V1.5）** | energy（精力按作息漂移）/ mood（情绪回基线）/ social_need（越久没被真回越渴望）；决策四层防打扰（勿扰墙/冷却/每日上限/未回上限）；依恋轴（焦虑/安全/回避）调制 |
| **生活模拟** | 小时段生活底色 + 非每日的日间残余梦境；动机卡片【现在】【今天】【昨天】【梦】【状态】——只讲真实发生的，不现编模板 |
| **Web 后台** | 人格调参 / 记忆可视化 / 主动状态机（三环仪表+参数滑块）/ 她的一天（生活底色编辑 + 「长一条」+「推一次」）/ 状态 |
| **成长** | 生活日志 `data/life_journal.md`，grow 按她真实生活底色生长当天记录 |

**默认档「自然淡雅」**：开启阈值 0.5、每日上限 2、勿扰 02:00–05:00、冷却 300s、依恋安全型。不催、不吵、走得近但留有分寸。

---

## 目录

```
girl/
├── active/                 # V1.5 主动状态机 + 生活模拟 + 心跳
│   ├── config.py           #   全部参数（唯一真相）
│   ├── state_machine.py    #   纯函数三方程 + 决策层 + 事件
│   ├── state_store.py      #   data/state.json 读写
│   ├── life_content.py     #   生活底色 data/life_content.yaml
│   ├── life_journal.py     #   生活日志 data/life_journal.md
│   ├── life_sim.py         #   当下活动 + 非每日梦境
│   ├── life_grower.py      #   生长当天生活记录
│   ├── motivation.py       #   动机卡片（社科细颗粒，不硬造）
│   ├── heartbeat.py        #   每 tick_minutes 推进状态
│   └── injector.py         #   单一出口：把卡片写进心跳文件
├── web/                    # FastAPI 伴侣后台
│   ├── main.py             #   入口 + lifespan(起心跳/挂路由)
│   ├── active_bridge.py    #   心跳线程 + /api/active/*
│   ├── soul_render.py      #   滑块 → SOUL.md 渲染器
│   ├── agent_admin.py      #   读写 girl_workspace + 会话
│   ├── templates/ static/  #   前端
│   └── README.md           #   后台使用说明
├── girl_workspace/         # OpenClaw girl agent 工作区（人格/规则/心跳钩子）
├── tests/                  # 42 个测试（pytest）
├── data/                   # 运行态：config.yaml / state.json / 生活 / 日志（本地）
└── app/, main.py           # （旧自研引擎，已由 OpenClaw 接管的占位）
```

---

## 启动

### 1. OpenClaw（她的"声音"）

```bash
openclaw daemon start        # 或按你本机的服务方式
openclaw status              # 网关/通道健康
```

确保 `girl` agent 绑定微信通道、工作区指向本仓库 `girl_workspace/`。

### 2. Web 伴侣后台（你的"遥控器"）

```bash
cd E:/college_information/girl
pip install -r web/requirements.txt   # 首次
python -m uvicorn web.main:app --port 18780
```

打开 http://127.0.0.1:18780

### 3. 主动行为（V1.5）

heartbeat 每 15 分钟推进一次状态；当全部守卫放行（阈值/冷却/每日上限/勿扰/未回）时才可能主动开口。想让小语真开口，把 `data/config.yaml` 的 `inject_provider` 从 `dry_run` 翻成 `openclaw`（生长对应 `grow_provider`）。**默认 `dry_run`，只拼卡片不真发**——先看清楚她要说什么，再放她出去。

---

## 测试

```bash
python -m pytest        # 42 passed
```

---

## 隐私与安全

- 记忆 / 人格 / 生活 / 日志 **100% 本机**，不入库、不上传。
- API key 与网关 token 潜伏于 OpenClaw 配置（`~\.openclaw\`），**从未进本仓库**。
- git 只跟踪代码 + README；`docs/`、运行态、生活数据等非必要文档/个人数据均忽略。
