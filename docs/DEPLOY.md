# DEPLOY — Windows 10 服务器部署手册（M0）

> 目标：OpenClaw（girl agent + DeepSeek）+ NapCat（QQ 个人号通道）在 Windows 10 上常驻运行。
> 本机只是写代码的机器——照着本文在服务器上做即可。
> 下文以 `D:\girl-rebuilt` 为仓库根目录，路径不同就改对应配置值。

---

## 0. 前置

- Windows 10 x64，管理员 PowerShell
- [Node.js 24 LTS](https://nodejs.org/)（`node -v` ≥ 24，含 npm）
- Git
- [DeepSeek 开放平台](https://platform.deepseek.com/) 的 API Key
- **一个当"小语"的 QQ 小号**（给 NapCat 登录）+ 你自己的主 QQ 号

## 1. 安装 OpenClaw

```powershell
npm install -g openclaw@2026.7.1-2
openclaw --version          # 应输出 2026.7.1-2
```

> 版本**固定在 2026.7.1-2**（旧项目验证过的版本）。升级前先重测通道插件兼容性。

## 2. 取得本仓库

```powershell
cd D:\
git clone <你的仓库地址> girl-rebuilt    # 或直接把目录拷过去
```

## 3. 写入配置与密钥

```powershell
# 环境变量（重开终端后生效）
setx DEEPSEEK_API_KEY "sk-你的key"

# 配置文件
mkdir "$env:USERPROFILE\.openclaw" -Force
copy D:\girl-rebuilt\deploy\openclaw.example.json "$env:USERPROFILE\.openclaw\openclaw.json"
notepad "$env:USERPROFILE\.openclaw\openclaw.json"
```

**必改 5 处**：

| 位置 | 改成 |
|---|---|
| `agents.list[0].workspace` | 服务器上的仓库工作区，如 `D:\\girl-rebuilt\\girl_workspace` |
| `channels.napcat.accessToken` | 自己生成一串随机 token（下一步 NapCat 用**同一个**） |
| `channels.napcat.admins` | `[你的主QQ号]`（数字，不带引号） |
| `gateway.auth.token` | 换成一串长随机 token（`openclaw daemon` 与后台通信用） |
| `models.providers.deepseek.apiKey` | 保持 `${DEEPSEEK_API_KEY}` 不动（走环境变量） |

## 4. 安装 QQ 通道插件

两个可选社区插件（选一个，以它的 README 为准）：

- [Daiyimo/openclaw-napcat](https://github.com/Daiyimo/openclaw-napcat) —— OneBot v11，正向 WS / 反向 WS / HTTP 三通道互备。本配置模板按它的键名写（`reverseWsPort` / `httpUrl` / `accessToken` / `admins`）。
- [ProperSAMA/openclaw-napcat-plugin](https://github.com/ProperSAMA/openclaw-napcat-plugin) —— 同类备选。

安装方式二选一：

```powershell
# 方式一：clone 后本地安装
git clone https://github.com/Daiyimo/openclaw-napcat D:\openclaw-napcat
openclaw plugins install D:\openclaw-napcat

# 方式二：openclaw.json 的 plugins.load.paths 指向插件目录
#   "plugins": { "load": { "paths": ["D:\\openclaw-napcat"] } }
#   （旧项目 send-feed 插件即此法，已验证可行）
```

> 插件 id 叫 `napcat` 时，本模板的 `channels.napcat` / `plugins.allow` 键名直接可用；
> 若插件 id 不同（如 `openclaw-napcat`），把这两处键名同步替换。

## 5. NapCat 侧（Windows 原生）

1. 服务器上安装 **QQ NT 客户端** + 下载 [NapCat.Shell](https://github.com/NapNeko/NapCatQQ/releases)（解压即用，跟随其 README 启动）。
2. 用**小号**扫码登录；NapCat 自带 WebUI（默认 `http://127.0.0.1:6099/webui`，首次 token 见启动日志）。
3. 在 WebUI「网络配置」里新建 OneBot11 配置：
   - **HTTP Server**：开启，端口 `3000`，token = 上一步的 accessToken，`messagePostFormat: array`
   - **反向 WebSocket Client**：`ws://127.0.0.1:3002`，同一个 token，`reconnectInterval: 5000`
4. NapCat 常驻：用其自带的无头/守护方式，或加一条开机计划任务，保证重启后自动登录。

> NapCat 与 OpenClaw 在同一台机器上，全程只走 `127.0.0.1`，不需要对公网开任何端口。

## 6. 启动 OpenClaw 网关

```powershell
openclaw daemon install    # 装成系统服务（Windows 计划任务）
openclaw daemon start
openclaw daemon status     # 服务状态 + 网关连通性
```

## 7. 验收（M0 的完成标准）

1. `openclaw channels status --probe` —— napcat 通道在线
2. 用**主号**给**小号**发一条消息 → 小语用中文、有性格地回复
3. 连续聊 10 条：不机械、不 AI 腔、一条消息不换行
4. **重启服务器**，再发一条 —— 网关与 NapCat 都自启、她还在
5. 第二天再聊 —— 还记得昨天聊过什么（进入 M1 验收）

## 8. 常见问题

| 症状 | 处置 |
|---|---|
| 通道不自启/不响应 | openclaw 2026.7.x 的 crash-loop breaker 会抑制反复失败的通道：修好 NapCat 后手动 `openclaw channels start napcat` |
| NapCat 反复 401/重连 | 两边 token 不一致；`accessToken` 必须与 NapCat OneBot 配置完全相同 |
| 她回 "The user is asking…" 英文旁白 | AGENTS.md 的语言铁律没被读进 system——检查 `agents.list[0].workspace` 路径是否指对 |
| 扫码登录过期 | NapCat WebUI 重新扫码；QQ 小号建议挂常亮设备避免风控下线 |
| 查日志 | `~/.openclaw/logs/`；NapCat 侧看 WebUI 日志页 |
| 想加回 qmd 深度检索 | M1 再说：装 qmd 后在 openclaw.json 加 `memory.backend: qmd`（参考旧项目配置） |

## 9. M2 预告（启用主动心跳时要动的地方）

- `openclaw.json`：`agents.list[0]` 加 `heartbeat` 块（every/activeHours/prompt，照旧项目收编）
- `plugins.load.paths` 加 `D:\girl-rebuilt\plugins\send-feed`，并设环境变量 `GIRL_SEND_FEED_PATH`
- 服务器建计划任务：每 15 分钟跑 `python -m active tick`（代码在 M2 里程碑落地）
