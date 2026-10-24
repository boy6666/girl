# send-feed 插件

按**触发源**把她的每一条真实发送机械记一行进 `girl_workspace/memory/send_feed.md`：

- 触发源 = 用户消息 → 追加 `__REPLY__`（她在回他）
- 触发源 = 心跳/cron/其它 → 追加 `__SELF__`（她自己主动发）

由 Python 心跳消费并清空——插件只追加，绝不清理，绝不发消息（单一出口）。
来源：旧项目（girl/openclaw-plugins/send-feed）已验证的实现；本版改动仅两处：
落点路径支持环境变量 `GIRL_SEND_FEED_PATH`、默认路径指向本仓库。

## 启用（M2 里程碑才需要，M0 保持关闭）

1. `openclaw.json`：

```json
"plugins": {
  "allow": ["deepseek", "napcat", "send-feed"],
  "entries": { "send-feed": { "enabled": true, "hooks": { "allowConversationAccess": true } } },
  "load": { "paths": ["D:\\girl-rebuilt\\plugins\\send-feed"] }
}
```

2. 环境变量（见 `deploy/env.example`）：

```powershell
setx GIRL_SEND_FEED_PATH "D:\girl-rebuilt\girl_workspace\memory\send_feed.md"
```

3. 若报找不到 `openclaw/plugin-sdk/plugin-entry`，在插件目录里给全局包做个链接：

```powershell
cd D:\girl-rebuilt\plugins\send-feed
mkdir node_modules -Force
mklink /D node_modules\openclaw "<npm全局目录>\node_modules\openclaw"
# npm 全局目录可用 npm root -g 查询
```
