# ROADMAP — 里程碑与旧功能取舍（唯一真相）

> 原则：**从能聊的内核开始，一层层堆功能；每一层结束时系统都完整可用。**
> 旧项目（`E:\college_information\girl`）评审结论：方向健康，债务集中在
> ①852 行 god module ②intake 协议 7 份复制 ③无锁非原子并发写。本路线已把这些结论吸收为工程铁律。

---

## M0 · 通 —— 能聊（当前里程碑）

**目标**：OpenClaw + DeepSeek + QQ(NapCat) + 精简人格。全部是配置与 markdown，**零 Python**。
**交付**：`deploy/openclaw.example.json` + `docs/DEPLOY.md` + `girl_workspace/` 四件套。
**验收**：QQ 私聊有来有回；说人话（短、不机械、不 AI 腔）；有性格；会话内记得住上下文。

## M1 · 忆 —— 记得住（无代码里程碑）

**目标**：验证并调优 OpenClaw 原生记忆。
- 跨天记忆实测（昨天聊的事今天能不能想起）；`memorySearch` 参数按实测调
- 记忆纪律已在 AGENTS.md（检索不整读）——按实测微调
- 可选：`memory.backend: qmd` 深度语义检索（需在服务器装 qmd）
**验收**：三天后她能自然提起前天的事。

## M2 · 主 —— 会找你（第一个 Python 里程碑）

**目标**：她会主动开口，且节奏克制、有真实由头。

| 组件 | 来源 | 形态（吸收重构结论） |
|---|---|---|
| `active/core/state_machine.py` | 照搬旧版（纯函数质量好，四扇卫门已拆） | energy/mood/social_need 三方程 + 开窗判定 |
| `active/core/state_store.py` | 重写 | **原子写(tmp+replace) + 锁**；损坏告警不静默归零 |
| `active/config.py` | 重写 | `ConfigRepo`：data/config.yaml **唯一读写口**（锁+原子写）；模板 = `config.example.yaml` |
| `active/channels/intake.py` | 新建 | `IntakeFile` 唯一抽象（谁写/谁清/追加或覆盖显式化）——旧项目 7 份复制的教训 |
| `active/engine/tick.py` | 收编旧 active_bridge 心跳职责 | **CLI：`python -m active tick`**，由 Windows 计划任务每 15 分钟调；**不做常驻线程、不寄生 web** |
| `plugins/send-feed/` | 已收编（本期启用） | 机械记账 `__REPLY__`/`__SELF__`，不靠自觉 |
| OpenClaw heartbeat | 旧配置收编 | `every: 30m` + activeHours + HEARTBEAT_OK 协议 + `PROACTIVE_INTAKE.md` |
| 动机卡片【现在】 | 收编旧 motivation | 简化版：只讲真实由头，社科原则保留在文档 |

**舍弃**：独立心跳线程、uvicorn 寄生、三份 tick 实现并存、`unanswered_count` 半死字段。

## M3 · 内 —— 有内心

- **反思 reflection**：`REFLECT_INTAKE.md` → `memory/reflections/YYYY-MM-DD.md`，可靠洞见升 MEMORY.md
- **日记 diary**：`DIARY_INTAKE.md` → `memory/diary/`；固定就寝窗口起步
- 可选后置：**作息漂移 circadian**（他晚睡我晚睡）、**梦 dream**（非每日、须真实由头）
- 可选后置：旧 `life_journal` 的 harvest 收编（若日记可检索则**永久舍弃**——两套日志是重复）

## M4 · 活 —— 有生活

- **生活底色** `data/life_content.yaml` + **当下活动** life_sim → 动机卡片【今天】
- **她的一天 life_day**（简化版：早上排一天 → 晚间日记对账；砍掉打断修正）
- **成长 growth**：GROWTH.md 低频（约 3 天）追加，真长才算，没长不硬写
- 可选：时刻表 scheduler、依恋轴（secure/anxious/avoidant 调制思念涨速）

## M5 · 台 —— 可观测

- **极简后台**：FastAPI 只读为主——状态页（三环仪表）+ 记忆/日记浏览 + 手动触发按钮
- 可选：人格滑块 → SOUL.md 渲染（soul_render 收编）
- **暂不做** context_proxy/meter/clean：上下文经济先靠纪律（见 CONTRACT §4），
  只有膨胀成为实际问题时再做计量与清洗

## M6 · 饰 —— 锦上添花

- **表情包 image 模式**（adesk/sogou 图源 → `data/media/`，TTL 清理；char 模式永久废弃）
- **人格滋养**（借鉴 [dsh-bili-humanism](https://github.com/InariNGT-Ofiicial/dsh-bili-humanism) 的机制，不装 DSH 本体）：
  定期让她"读一点她世界里的内容"（文章/视频字幕）→ 信笺区分 **事实 / 作者观点 / AI 推测** →
  每天最多一句写进 `human-world.md` → agent 分页只读最近 7 条。
  **上限就是设计**：允许没有新认识，"不必每天凑一句"。
- 可选：记忆图谱（纯观赏）、语音/图片（先实测通道富媒体支持）

---

## 旧功能取舍总表

| 旧项目功能 | 去向 | 理由 |
|---|---|---|
| OpenClaw 宿主 + 通道 + 原生记忆 | M0/M1 直接复用 | 已验证，不自研 |
| AGENTS.md 行为纪律 | M0 精简收编（~1/3 长度） | 战斗检验过的"人味"规则是核心资产 |
| SOUL/IDENTITY/USER 人格 | M0 收编（去滑块段） | 同上；滑块 M5 再回来 |
| 状态机三方程 | M2 照搬 | 纯函数、有强测试 |
| 心跳循环（常驻线程） | M2 改计划任务 + CLI | 根治"寄生 web / 线程猝死" |
| 动机卡片【现在】 | M2 简化收编 | 主动性的核心 |
| send-feed 记账 | M2 启用（已收编本仓库） | 机械判定 > 自觉汇报 |
| 注入通道矩阵 inject_channels | M2 起简化为 config 段 | 通道从 9 个减到 2-3 个再谈矩阵 |
| 反思 / 日记 | M3 | 内心生活的地基 |
| 梦 / 作息漂移 / 时刻表 | M3/M4 可选 | 彩蛋性质，核心跑通后再加 |
| 生活底色 / life_sim / 她的一天 | M4 简化版 | "她有自己的日子" |
| 成长 growth | M4 | Erikson 亲密度在关系里继续发育 |
| life_init（初始化年龄） | **舍弃** | 一次性仪式，价值低 |
| life_journal + grower | **舍弃**（并入日记） | 两套日志重复 |
| relations 关系表 | M4 可选 | 依恋轴才用得到 |
| memgraph 记忆图谱 | M6 可选 | 纯观赏 |
| emoji char 模式 | **永久舍弃** | 旧项目已拍板废弃 |
| emoji image 模式 | M6 | 稳定图源已验证 |
| context_proxy / meter / clean | **暂不做** | 用纪律解决；问题重现再做 |
| Web 后台全套 | M5 极简版 | 旧后台是 852 行 god module 的主要成因 |
| app/ 旧自研引擎 | **永久舍弃** | 死代码，零 import |
| 四扇防打扰卫门 | **永久舍弃** | 旧项目 8-21 已拍板拆除；勿扰交给 heartbeat activeHours |
| `unanswered_count` 展示字段 | **舍弃** | 无决策消费的半死字段 |

## 工程铁律（全程生效，来自重构评审）

1. **单一出口**：QQ 消息只由 OpenClaw 发；Python 只写 intake 卡片。
2. **intake 唯一抽象**：所有钩子文件读写走 `IntakeFile`，不许出现第二份复制。
3. **两个唯一读写口**：`ConfigRepo`（config.yaml）与 `StateStore`（state.json），原子写 + 锁。
4. **状态机纯函数、时间显式传参**；tick 由计划任务调 CLI，不做常驻线程。
5. **上下文经济**：见 `docs/CONTRACT.md` §4——这是旧项目"上下文过长"的根治方案。
6. **每期有测试**；协议类测试（intake 写格式 = 跨进程契约）先行。
7. **仓库卫生**：tmp 文件禁入根目录；运行态与私人数据 gitignore 先行；密钥只走环境变量。
