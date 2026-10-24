# girl-rebuilt · 从零重构的「她」

一个**尽可能有人类情感、有自己个性、过着自己生活**的 AI 伴侣。
她跑在 OpenClaw 上（她的声音 + QQ 通道）；她的魂是几个 markdown 文件；Python 在后面的里程碑里逐层给她的内在（状态机 → 主动 → 反思 → 生活 → 成长）。

> 前身是 `E:\college_information\girl`（小语）。那次重构评审的结论是：方向健康、债务集中。
> 本仓库**只从最小的能聊内核开始，按里程碑逐层堆功能**，每个里程碑都可用、可回退。

---

## 架构（M0 现状）

```
┌──────────┐   NapCat(OneBot11)   ┌───────────────────────────┐
│  QQ App  │ ◄──────────────────► │      OpenClaw Gateway      │
│  (你)    │   ws://…:3002 反向WS  │   ┌─────────────────────┐ │
└──────────┘                      │   │  girl agent          │ │
                                  │   │  AGENTS.md 行为规则   │ │
                                  │   │  SOUL.md 人格        │ │
                                  │   │  IDENTITY/USER/MEMORY│ │
                                  │   │  session + 记忆检索   │ │
                                  │   └─────────────────────┘ │
                                  └─────────────┬─────────────┘
                                                │ OpenAI 兼容
                                      ┌─────────▼─────────┐
                                      │  DeepSeek API      │
                                      │  (v4-flash 主力)   │
                                      └───────────────────┘
```

**铁律：消息出口只有一个。** QQ 收发全部由 OpenClaw 负责；以后 Python 只往
`girl_workspace/memory/` 里写"素材卡"让她自己决定说不说（见 `docs/CONTRACT.md`）。

## 当前状态：M0 · 能聊

- [x] OpenClaw + DeepSeek 通道（配置见 `deploy/openclaw.example.json`）
- [x] QQ 个人号通道（NapCat / OneBot v11）
- [x] 精简人格四件套 + 记忆骨架（`girl_workspace/`）
- [ ] 部署验收 → 跟着 `docs/DEPLOY.md` 在 Windows 10 服务器上跑通

**M0 没有任何 Python。** 能聊、有人味、有性格，就够格进 M1。

## 路线图

`ROADMAP.md` 是唯一真相：旧项目每个功能"收编到哪一期 / 为什么舍弃"都在那张表里。

- M1 忆 · 记得住（调优原生记忆，无代码）
- M2 主 · 会找你（状态机 + 心跳 + 主动卡片，第一个 Python 里程碑）
- M3 内 · 有内心（反思 / 日记）
- M4 活 · 有生活（生活底色 / 她的一天 / 成长）
- M5 台 · 可观测（极简后台）
- M6 饰 · 锦上添花（表情包 / 人格滋养 / 图谱）

## 目录

```
girl-rebuilt/
├── README.md                  # 本文件
├── ROADMAP.md                 # 里程碑 + 旧功能取舍总表（唯一真相）
├── docs/
│   ├── DEPLOY.md              # Windows 10 服务器部署手册
│   └── CONTRACT.md            # 契约与红线（单一出口 / intake / 上下文经济）
├── deploy/
│   ├── openclaw.example.json  # OpenClaw 配置模板（DeepSeek + NapCat + girl agent）
│   └── env.example            # 环境变量模板（密钥不落配置、不入库）
├── girl_workspace/            # 她的工作区（魂）
│   ├── AGENTS.md              # 行为规则（什么时候开口/闭嘴/怎么说话）
│   ├── SOUL.md                # 人格（她是谁）
│   ├── IDENTITY.md            # 身份
│   ├── USER.md                # 他是谁（待相处填全）
│   ├── MEMORY.md              # 长期记忆骨架
│   └── memory/                # 运行态（gitignored）：会话产物/收件箱
└── plugins/
    └── send-feed/             # 发送记账插件（M2 启用；已按新路径改造）
```
