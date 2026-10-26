# TROUBLESHOOTING — 部署避坑手册

> 2026-10-25 首次部署（Windows 10 + OpenClaw 2026.10.7 + NapCat + DeepSeek）的实战踩坑全记录。
> 格式：症状 → 根因 → 解法。**遇到报错先查这张表，能省一整天。**

## 0. 排查心法

- **先分清查哪本日志**：收发问题看 NapCat 控制台/WebUI；agent / 模型 / 派发问题看**网关日志**
  `%LOCALAPPDATA%\Temp\openclaw\openclaw-YYYY-MM-DD.log`（可读化命令见 §5）。
- 改完配置先 `openclaw config validate`——这个版本对未知键**直接报错**，报错信息很准。
- 供应商先独立验证再接进网关（别让网关替你试错）：
  `curl.exe -s https://api.deepseek.com/models -H "Authorization: Bearer sk-..."`

## 1. 插件安装

| 症状 | 根因 | 解法 |
|---|---|---|
| ClawHub 装 napcat 报 `requires compiled runtime output ... expected ./dist/index.js` | 该发布包只有 TS 源码、没有编译产物（发布者打包问题） | 改源码安装：`git clone` → `npm install` → `npm run build` → `openclaw plugins install <本地目录>` |
| `npm install` 后 build 失败 / 运行时原生模块缺失 | 新版 npm 的 install-scripts 白名单拦了 esbuild/koffi 的 postinstall | 插件目录里 `npm install-scripts approve` 后重装；纯文字聊天不受影响 |

## 2. 配置与网关

| 症状 | 根因 | 解法 |
|---|---|---|
| `gateway status` 警告 `env var "DEEPSEEK_API_KEY" - feature ... unavailable` | 网关以 **S4U 计划任务**运行，吃不到用户级 `setx` 变量 | key 直接内联进 openclaw.json（回环部署可接受，日后可换 `setx /M` 系统级或 vault） |
| 启动即退 + `Unrecognized keys: "codex", "napcat"` | onboard 向导 / 插件启用往顶层写的键不被识别 | 删掉这些顶层键；每次改完先 validate |
| `agents.ownership: multi-agent rosters require agents.ownership="explicit"` | 多 agent 名册必须显式声明归属 | `agents` 里加 `"ownership": "explicit"` |
| bindings 看着配了、消息却派发到默认 agent | ① 省略 `accountId` 只匹配渠道**默认账号**，全渠道要显式 `"*"`；② 旧版 `type: "route"` 字段已废弃 | binding 写全：`{ "agentId": "...", "match": { "channel": "napcat", "accountId": "*" } }` |
| `Reply dispatch error: prepared reply dispatch runtime owner was not published for default` | **napcat 插件把 `agent:default` 硬编码进 sessionKey**（`dist/src/gateway/inbound.js` 三处模板字符串），不读任何 agent 配置键 | 在 `agents.entries` 里放一个 **id 叫 "default"** 的 agent，workspace 指向人格目录；bindings 也指向它。名字可以叫 girl，**id 必须叫 default** |
| `SQLite ... openclaw-agent.sqlite belongs to agent default; requested agent girl` | agent 数据库内部**盖了归属章**：agentDir 与 agent id 必须一一对应 | 复用旧 agent 目录时 id 必须一致；新 agent 用全新 agentDir，别张冠李戴 |
| 改了 `agents.entries` 后网关反复重启/启动失败 | 热重载只覆盖 models、defaults.model 等**值**变更；结构性变更（entries/bindings）必须重启 | 按提示 `gateway stop` + `start`，**等满 60 秒**再测（启动链约 45-50 秒） |
| 网关子进程被杀，日志见 `event_loop_delay P99` 数百秒 | 事件循环卡死伴随 SQLite 锁竞争风暴（本次由路由错误的重试引发） | 先修路由根因；复现时 `openclaw gateway status` 看 Readiness，stop/start |

## 3. 模型（DeepSeek）

| 症状 | 根因 | 解法 |
|---|---|---|
| 配置看着全对、模型调用必失败 | **API 模型改名漂移**：2026-08 的 `deepseek-v4-flash` / `deepseek-chat` 到 2026-10 已下线，现役是 `deepseek-flash`（=V4.1，支持图片输入）和 `deepseek-v4-pro` | **永远以 `curl https://api.deepseek.com/models` 的实际目录为准**写 models 块和 primary/fallbacks |
| `Authentication Fails` | key 错；或 PowerShell 里 `-H` 后只给了 key、丢了 `Authorization: Bearer` 前缀 | 用 `Invoke-RestMethod -Uri "https://api.deepseek.com/models" -Headers @{ Authorization = "Bearer <key>" }` 更稳 |

## 4. NapCat / QQ 通道

| 症状 | 根因 | 解法 |
|---|---|---|
| probe 超时、消息进不来 | 反向 WS 客户端 URL 是**默认占位 `ws://localhost:8082`**，没改 | WebUI 里改成 `ws://127.0.0.1:3002`（名称栏只是标签，别被它骗） |
| 能收不能回（或只有错误兜底消息） | NapCat 的 **HTTP Server（发送腿）没启用** | WebUI 启用 HTTP Server：`127.0.0.1:3000`，token 与 openclaw.json 的 accessToken 一字不差，消息格式 array |
| 反复 401/重连 | 两边 token 不一致 | 逐字符核对 NapCat 两条配置与 `channels.napcat.accessToken` |
| QQ 自动掉线 | **两个电脑端（NT 客户端）互踢**（手机+电脑可共存）；probe 不会踢人 | 小号固定在服务器 NapCat 登录、手机保持在线；设备管理里清掉多余电脑端 |
| NapCat 内部报 `消息undefined不存在` | NapCat 对过期/撤回消息的 API 调用报错 | 噪音，忽略 |
| `channels status --probe` 对 napcat 30s 超时（其余状态 connected） | NapCat 的 status 接口实现挂起 | **已知噪音**：收发正常就以实际消息为准，别被它带偏排查方向 |

## 5. 网关日志可读化（复制即用）

```powershell
Get-Content $env:LOCALAPPDATA\Temp\openclaw\openclaw-2026-10-25.log -Tail 400 | ForEach-Object { try { $j = $_ | ConvertFrom-Json; "[$($j.time)] $($j._meta.logLevelName): $($j.message)" } catch {} } | Select-String -Pattern "girl|default|dispatch|deepseek|model|ERROR" | Select-Object -Last 20
```

## 6. 运维杂项

- **PowerShell 粘贴带中文行内注释的命令** → 乱码被当成参数，报 `Too many arguments`。命令保持纯 ASCII，说明写在单独一行。
- 2026.10.x 子命令是 `openclaw gateway install / start / stop / status`（旧版的 `daemon install/start` 已换名）。
- **服务器上 git 仓库 = 代码 + 模板**。一切运行态都在仓库外：live 配置（`~\.openclaw\`）、她的工作区（`D:\girl-data\workspace`）。**永远不要在服务器上直接改仓库内的文件**——否则下次 pull 必冲突。
