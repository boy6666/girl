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
| **反思（V3）** | 每晚/重要对话后自我抽离地复盘：命名情绪、纳进「你和我」的叙事、可靠洞见升长期记忆。默认 `reflection.provider: dry_run`（只拼诉求注入），翻 `openclaw` 由小语写进 `memory/reflections/`。产物内化、零发送 |
| **记忆图谱（V3）** | 读侧投影：把她记忆文件（USER/MEMORY/日记/反思/生活日志）抽成人物-主题-记忆点，Web 台轻量 SVG 力导向展示；提及你的必连中心「你」。零写、零发送、纯本地 |
| **表情（②）** | 情绪/关键词 → 表情：字符出口（本地标注数据集 + 1 个 emoji 字符）或图源出口（adesk/sogou 稳定 API → 表情图 URL）；默认 `off` |

**默认档「自然淡雅」**：开启阈值 0.5、每日上限 2、勿扰 02:00–05:00、冷却 300s、依恋安全型。不催、不吵、走得近但留有分寸。

---

## 设计依据（社科研究）

小语的主动节奏、开口内容和防打扰底线**不是随手拍的**，每条都锚定在社会心理学 / 亲密关系研究上：

| 机制 | 落到小语哪里 |
|---|---|
| **社会渗透理论** | 分享「日常/喜好」先于深度情绪，情感性 > 事实性，随互惠渐进加深、不一步到深处 |
| **日常仪式 / 维系策略** | 主动走「routine > strategic」：晨/午/晚自然锚点、可跳过、低摩擦，不刻意挑时机强聊 |
| **capitalization（分享放大）** | 每次分享好消息 + 有温度地回应，胜过高频轰炸——**次数克制、每回有内容** |
| **逆反理论** | 永不索求回复——越催越不想理，所以她只给不讨 |
| **缺席 + 补偿** | 允许「去过自己的生活」制造自然稀缺（如能量低时陪自己的事），但归来给高质量回应、不真空断联 |
| **依恋理论** | 人格挂依恋轴（安全 / 焦虑 / 回避），默认**安全型** = 主动但不黏、尊重你的节奏 |
| **反思 vs 反刍** | 小语反思是自我抽离、好奇、产光亮（reflection）；一旦绕圈焦虑就是反刍（rumination），健康判别：落笔要有一个「更懂」的沉淀，否则收起笔等明天 |
| **叙事同一性** | 她把每天碎片按「你和我正在发生的故事」编进一致的自我叙事，让关系更韧、她不散 |
| **情绪标记** | 睡前给出情绪的名字（「其实今天有点难过」）是调节不是放大——廉价而真实的自我照护 |
| **叙事同一性 · 可见化** | 记忆图谱展示她如何把碎片编成"关于你和她的故事"——读侧投影，不引导她说话，仅供你看她积累的内心 |
| **思念累积** | 对应 `social_need = 1−e^(−λt)`：越久没被**真回**越渴望，且**只有真回才归零**；沉默也是合法选择 |

> 动机卡片只用她**真实发生过**的生活（今天 / 昨天 / 梦 / 状态）取料，不现编死板模板——宁可少而实，不留活泼的空话。依据见设计文档 `docs/superpowers/specs/2026-08-11-active-state-machine-life-sim-design.md` §2（社科侧）。

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
│   ├── emoji_matcher.py    #   表情解析层：情绪/关键词→字符 or 图 URL
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
├── tests/                  # 97 个测试（pytest）
├── data/                   # 运行态：config.yaml / state.json / 生活 / 日志（本地）
└── app/, main.py           # （旧自研引擎，已由 OpenClaw 接管的占位）
```

---

## 启动与配置

系统分两半：**OpenClaw**（她的声音 + 微信出口）和 **Web 伴侣后台**（你的遥控器 + V1.5 状态机）。两边都起来才是一个完整的小语。

### 0. 一次性初始化 OpenClaw（首次）

```bash
openclaw configure --section model     # 配模型 provider：DeepSeek API key（本机 ~\.openclaw\，不入库）
openclaw configure --section gateway   # 网关/服务（可选）
```

**接入微信通道**（ClawBot 插件）：

```bash
openclaw channels add --channel openclaw-weixin   # 引导式登录微信（扫码/协议）
openclaw channels status --probe                  # 探活通道
```

**准备 `girl` agent**（本仓库已随 `girl_workspace/` 带好人设，关键一步是让它的工作区指向这里）：

```bash
openclaw agents list        # 确认 girl 存在
openclaw agents add         # 没有则新建（id: girl）
openclaw agents bind        # 建路由：openclaw-weixin → girl（微信进来走 girl）
```

> 她读的文件都在 `girl_workspace/`：`SOUL.md`（人格·滑块渲染目标）、`AGENTS.md`（行为规则）、`IDENTITY.md`（名字/设定）、`USER.md`（关于你）、`HEARTBEAT.md`（主动心跳钩子）。

### 1. 启动 OpenClaw 服务（她的"声音"）

```bash
openclaw daemon install     # 首次：装成系统服务（Windows: schtasks 计划任务）
openclaw daemon start
openclaw daemon status      # 服务状态 + 网关连通性
openclaw channels status --probe   # 微信通道在线？
openclaw agents list                # 确认 girl 已绑定 openclaw-weixin
```

确认：`girl` agent 绑定微信通道、工作区指向本仓库 `girl_workspace/`（见 `active/` 从 `girl_workspace/memory/heartbeat.md` 读动机卡片）。

### 2. 启动 Web 伴侣后台（你的"遥控器"）

```bash
cd E:/college_information/girl
pip install -r web/requirements.txt   # 首次
python -m uvicorn web.main:app --port 18780
```

打开 http://127.0.0.1:18780（后台细节见 `web/README.md`）

### 3. 主动行为（V1.5）

heartbeat 每 15 分钟推进一次状态（`tick_minutes`）；当**全部守卫放行**（阈值/能量/勿扰/冷却/每日上限/未回上限）时才可能主动开口。想试运行、看她会说什么而不真发：保持默认 `dry_run`，在后台「她的一天」点「现在就推」看卡片。想让小语真开口，把 `data/config.yaml` 的 provider 翻成 `openclaw`：

| 键 | 默认 | 含义 |
|---|---|---|
| `inject_provider` | `dry_run` | 动机卡片怎么送：`dry_run` 只拼不真发；`openclaw` 写进心跳文件由小语决定说不说 |
| `grow_provider` | `dry_run` | 生活日志怎么长：`dry_run` 用你填的底色拼接；`openclaw` 由小语用自己声音写当天 |

**关键参数表**（`data/config.yaml` → `active_behavior`）：

| 键 | 默认 | 含义 |
|---|---|---|
| `open_threshold` | 0.5 | social_need 达到多少才考虑开窗 |
| `cooldown_seconds` | 300 | 主动冷却（秒） |
| `daily_max` | 2 | 每日主动上限（次） |
| `quiet_start` / `quiet_end` | 2 / 5 | 勿扰硬墙时辰（绝不在此时主动） |
| `max_unanswered` | 3 | 连续未回上限（达到暂停催人） |
| `allow_late_night` / `late_night_start` / `early_morning_end` | true / 23 / 6 | 深夜软窗口 |
| `tick_minutes` | 15 | 心跳间隔 |
| `growth_rate_per_hour` | 0.12 | 思念涨速（每小时基数） |
| `energy_time_constant_min` | 240 | 精力漂移常数（4h） |
| `mood_time_constant_min` | 360 | 情绪回基线常数（6h） |
| `mood_baseline` | 0.15 | 情绪基线 |
| `attachment` | `secure` | 依恋类型：`secure` / `anxious` / `avoidant`（调制思念涨速） |
| `seed_energy` / `seed_mood` | 80.0 / 0.2 | 首次 tick 种子状态 |

**⚠️ 切真前**：先在「她的一天」页用「现在就推」（试跑）看卡片和小语的反应，确认无误再把 `inject_provider` 翻成 `openclaw`。默认全程 `dry_run`，Python 后端永不直接发微信。

### 4. 表情源配置（② 表情包语义匹配）

小语的情绪/关键词可以变成一个**表情**，两个出口二选一（`data/config.yaml` → `active_behavior.emoji_mode`）：

| 模式 | 行为 | 特点 |
|---|---|---|
| `off` | 关闭表情出口（**默认**） | 接真前保持现状 |
| `char` | 按本地标注数据集 → **1 个 emoji 字符** | 纯文本、嵌套在同一条消息里、微信原生渲染、零发送成本 |
| `image` | 按情绪/关键词调稳定图源 API → **表情图 URL** | 要真发图需先接真/开 IMAGE 通道 |

- **字符出口（char）**：数据来自 `data/emoji/`（EmoTag 150 表情×8 情绪 + Emoji Sentiment Ranking 751 表情×极性，本地自用 ~第三方数据集，gitignored）。状态机 mood/energy → 情绪 → 在 EmoTag 按情绪分取榜首、用 ESR 极性 tie-break，**只出 1 个**（反 AI 腔「一个就够」）。数据集缺失自动降级到内置兜底表，不崩。
- **图源出口（image）**：稳定 JSON 图源两个（均实测）：`adesk`（`so.picasso.adesk.com`）、`sogou`（`image.sogou.com/napi/wap/pic`），多源顺序 fallback。其余（doutula/fabiaoqing 等）是 HTML 抓取、实测不稳，**未收录**。
- **image 真发图**：`emoji_mode: image` 时，窗口一开 Python 会从稳定图源抓一张表情图、下载到本地「表情包文件夹」`data/media/`（gitignored），把**本地路径**写进动机卡片；girl 心跳读到后想发就用 `message(action=send, path=...)` 真发。**默认只发表情包本身**（表情包里已有文字），需要时她可在前/后配一句。图片默认单发、由小语判断；图源失败自动退回纯文字主动，不崩。回滚 = `emoji_mode` 翻回 `off`。
- **本地文件夹**：`data/media/` 自动建，旧图按 `emoji_media_ttl_days`（默认 14 天）自动清理。
- **配置**：`emoji_mode`（off/char/image）+ `emoji_sources`（图源列表）。改完重启后台生效。想自挂图源：补 `active/emoji_matcher.py` 的 `SOURCES` 条目，或在此覆盖 providers。
- **试跑**：后台 `GET /api/active/emoji/resolve?emotion=开心&mode=char`（或带 `mode=image`）看解析结果——全程 dry-run，不真发。
- image 出口**只解析到 URL**，不发图；真发图走单一出口（OpenClaw），先接真再切 `image`。

> 无密钥配置模板见仓库根 `config.example.yaml`（复制为 `data/config.yaml` 后按需改，密钥/token 勿提交）。

---

## 测试

```bash
python -m pytest        # 97 passed
```

---

## 隐私与安全

- 记忆 / 人格 / 生活 / 日志 **100% 本机**，不入库、不上传。
- API key 与网关 token 潜伏于 OpenClaw 配置（`~\.openclaw\`），**从未进本仓库**。
- git 只跟踪代码 + README；`docs/`、运行态、生活数据等非必要文档/个人数据均忽略。
