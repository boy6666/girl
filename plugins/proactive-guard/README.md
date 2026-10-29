# proactive-guard 插件

主动系统的**数据层**（P1 主菜）：按触发源把她每条真实发送机械分类记录，维护两个数字供心跳裁决：

- `selfToday` —— 今天她主动发了几条
- `unanswered` —— 最后一次"回他"之后，她连发了几次主动（他连续几次没理）

状态文件：`girl_workspace/memory/proactive_state.json`（每次发送后重算）。
明细日志：`girl_workspace/memory/proactive_log.md`（`[时间戳] REPLY|SELF`，留痕可审计）。

## 心跳裁决规则（写在心跳 prompt 里，数据在这里）

| 读到的状态 | 裁决 |
|---|---|
| `selfToday ≥ 2` | `HEARTBEAT_OK` —— 今日主动额度用完 |
| `unanswered ≥ 4` | `HEARTBEAT_OK` —— 他连续 4 次没理你的主动，**今天收手，绝不加码** |
| `unanswered = 1~3` 且静默够、有真实由头 | 可以开口，**语气按次数递进**：1 轻快自然 → 2 有点想念 → 3 小失落（不抱怨、不质问） |
| 其它 | 按静默阈值和由头标准正常裁决 |

设计照抄大肥鱼 proactive_chat 的两条硬规矩：**配额是上限不是 KPI**（允许一天 0 条）+ **退让是硬停不是降频**。

## 启用（与 send-feed 插件同法）

1. `openclaw.json`：

```json
"plugins": {
  "load": { "paths": ["D:\\girl-xiaoyu\\plugins\\send-feed", "D:\\girl-xiaoyu\\plugins\\proactive-guard"] },
  "entries": { "proactive-guard": { "enabled": true } }
}
```

（`plugins.allow` 数组里加 `"proactive-guard"`。）

2. 环境变量（可省略，默认值已指向小语工作区）：

```powershell
setx GIRL_SESSION_PREFIX "agent:default"
setx GIRL_PROACTIVE_LOG "D:\girl-xiaoyu\girl_workspace\memory\proactive_log.md"
setx GIRL_PROACTIVE_STATE "D:\girl-xiaoyu\girl_workspace\memory\proactive_state.json"
```

3. `openclaw gateway stop` → `start`，日志确认插件加载。

## 来源

触发源分类逻辑与 send-feed 同源（before_agent_run/message_sent/agent_end 三个已验证钩子）；
退让与情绪递进的设计抄自大肥鱼 proactive_chat（`max_unanswered_times` + `{{unanswered_count}}`），
状态文件对应其 `session_data.json`。插件只记账，绝不发消息（单一出口）。
