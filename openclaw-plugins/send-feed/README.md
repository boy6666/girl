# send-feed 插件

在网关传输层机械判定「她发的每条消息是回他 / 主动」，追加一行到
`girl_workspace/memory/send_feed.md`。替掉靠她自觉写 `__REPLY__/__SELF__` 标记的环节。

**分类**（来自类型化插件的 `before_agent_run` 触发源）：
- `trigger === "user"` → `__REPLY__`（在回主人的新消息）
- 其它（`heartbeat`/`cron`/缺失）→ `__SELF__`（自己主动发）

**单出口铁律**：这里只写磁盘卡片，绝不碰微信；Python 端 `active/send_feed.py`
消费者读后打回状态机并重置文件。

**安装**（做一次即可）：
```
openclaw plugins install -l E:\college_information\girl\openclaw-plugins\send-feed
openclaw plugins enable send-feed
```
并在 `openclaw.json` 的 `plugins.entries.send-feed` 里开
`"hooks": { "allowConversationAccess": true }`（因为用了 before_agent_run/agent_end，
属 conversation hooks），然后重启 gateway。

**回滚**：`openclaw plugins disable send-feed`（或 uninstall）并重启 gateway。
