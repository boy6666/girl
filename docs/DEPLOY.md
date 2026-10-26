# DEPLOY — Windows 10 服务器部署手册（实战版）

> 2026-10-25 全流程实战通过。版本基线：**OpenClaw 2026.10.7** + NapCat.Shell + DeepSeek。
> 遇到任何报错先查 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**——今天踩的坑全在那里。
> 下文以 `D:\girl-rebuilt` 为仓库根目录、`D:\girl-data` 为数据目录，路径不同就改对应值。

---

## 0. 部署形态（先读，决定了后面所有步骤）

**仓库 = 代码 + 模板。运行态全部在仓库外**，这是服务器 `git pull` 永不冲突的保证：

| 东西 | 位置 | 进 git？ |
|---|---|---|
| 代码 + 配置模板 + 人格模板 | `D:\girl-rebuilt`（本仓库） | ✅ |
| **live 网关配置** | `%USERPROFILE%\.openclaw\openclaw.json` | ❌ 本来就在仓库外 |
| **她的工作区（人格实例 + 记忆 + 会话）** | `D:\girl-data\workspace`（首次部署从仓库 `girl_workspace` 复制） | ❌ 运行态 |

**agent 命名铁律**：napcat 插件把 `agent:default` **硬编码**进会话键（源码 `inbound.js` 三处，不读任何配置）。
所以 OpenClaw 里**必须存在 id 叫 `default` 的 agent**（identity/name 可以叫 girl），workspace 指向数据目录。
另：agentDir 下的数据库盖了归属章，**agentDir 与 agent id 一一对应**，不能张冠李戴。

## 1. 前置

- Windows 10 x64，管理员 PowerShell
- Node.js ≥ 24.15（`node -v`）
- Git、[DeepSeek API key](https://platform.deepseek.com/)
- **一个当"小语"的 QQ 小号** + 你的主号（小号先加主号好友）

## 2. 安装 OpenClaw

```powershell
npm install -g openclaw
openclaw --version
```

> 2026.10.x 的子命令是 `openclaw gateway install/start/stop/status`（旧版的 `daemon` 已换名）。

## 3. 取仓库 + 建数据目录

```powershell
cd D:\
git clone -b rebuilt <你的仓库地址> girl-rebuilt
mkdir D:\girl-data -Force
Copy-Item -Recurse D:\girl-rebuilt\girl_workspace D:\girl-data\workspace
```

## 4. 写配置

```powershell
mkdir "$env:USERPROFILE\.openclaw" -Force
copy D:\girl-rebuilt\deploy\openclaw.example.json "$env:USERPROFILE\.openclaw\openclaw.json"
notepad "$env:USERPROFILE\.openclaw\openclaw.json"
```

**必改 5 处**：

| 位置 | 值 |
|---|---|
| `agents.entries.default.workspace` | `D:\\girl-data\\workspace`（注意双反斜杠） |
| `models.providers.deepseek.apiKey` | **直接内联真实 key**（S4U 服务吃不到用户级环境变量，详见 TROUBLESHOOTING §2） |
| `channels.napcat.accessToken` | 自拟随机串（NapCat 侧要用**同一个**） |
| `channels.napcat.admins` | `[你的主号QQ号]` |
| `gateway.auth.token` | 长随机串 |

模型 ID 以实测目录为准，部署前核对一次（模型会改名，这是真踩过的坑）：

```powershell
curl.exe -s https://api.deepseek.com/models -H "Authorization: Bearer 你的key"
```

最后**必须校验干净**：

```powershell
openclaw config validate
```

## 5. 装 QQ 通道插件（napcat，源码安装）

```powershell
git clone https://github.com/Daiyimo/openclaw-napcat D:\openclaw-napcat
cd D:\openclaw-napcat
npm install
npm run build
openclaw plugins install D:\openclaw-napcat
openclaw plugins list | Select-String napcat
```

> 插件 manifest id 是 `napcat`——openclaw.json 的 `channels.napcat` / `plugins.allow` / `bindings` 键名与它对应。
> ClawHub 市场上的 TS-only 包目前装不上（缺编译产物），别浪费时间。

## 6. NapCat 侧

1. 装 [NapCat.Shell.Windows.OneKey](https://github.com/NapNeko/NapCatQQ/releases)（或 QQ NT + NapCat.Shell，Win10 用 `launcher-win10.bat`）。
2. **用小号扫码登录**。以后小号的电脑端登录固定在这台服务器（两个电脑端会互踢），手机保持在线。
3. WebUI → 网络配置 → OneBot11，**两条**：
   - **HTTP Server**：`127.0.0.1:3000`，token = accessToken，消息格式 `array` ——这是**发送腿**，不开她回不了话
   - **反向 WebSocket 客户端**：URL **`ws://127.0.0.1:3002`**（默认占位是 8082，必须改），同 token，重连 5000ms
   - CORS 不开、SSL 不开、正向 WS 不开（全在本机回环，开了纯增加故障点）
4. NapCat 设开机自启（自带守护方式或计划任务）。

## 7. 启动与验收

```powershell
openclaw gateway install
openclaw gateway start
openclaw gateway status        # 等满 60 秒再看：无 Config warnings、Connectivity ok
openclaw agents list --bindings  # 确认 default(girl) 带 napcat accountId=* 规则
```

**验收 = 真实消息**：主号私聊小号 → 她用中文、带性格地回复（第一句可能记得之前的测试消息，正常）。
`channels status --probe` 对 napcat 超时是**已知噪音**（NapCat status 接口的问题），不影响收发，别被带偏。

重启服务器后再发一条——网关与 NapCat 都自启、她还在，部署才算稳。

## 8. 日常更新（git pull 永不冲突的原理）

```powershell
cd D:\girl-rebuilt
git pull origin rebuilt
```

- 仓库里只有代码和模板 → pull 不会撞上任何运行态。
- 若模板有更新（`girl_workspace/` 下），手动把差异同步到 `D:\girl-data\workspace`（先 diff 再拷，别整目录覆盖她的记忆）。
- **铁律：永远不要在服务器上直接改仓库内文件**；live 配置改 `~\.openclaw\openclaw.json`，人格/记忆改 `D:\girl-data\workspace`。

## 9. M2 预告（启用主动心跳时）

- `openclaw.json`：`agents.entries.default` 加 `heartbeat` 块（every/activeHours/prompt）
- `plugins.load.paths` 加本仓库 `plugins\send-feed`，并设环境变量 `GIRL_SEND_FEED_PATH=D:\girl-data\workspace\memory\send_feed.md`
- 计划任务：每 15 分钟 `python -m active tick`（代码随 M2 落地）

## 10. 报错速查

→ **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**：ClawHub 插件装不上、env var 不可用、模型改名漂移、
`runtime owner was not published`、SQLite 归属章、反向 WS 8082 占位、QQ 互踢、probe 噪音、日志可读化命令……全在。
