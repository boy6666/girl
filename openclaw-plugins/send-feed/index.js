// send-feed 插件：在网关传输层机械判定「她发的每条消息是回他还是主动」，
// 追加一行到 memory/send_feed.md。单出口铁律：这里只写卡片，绝不碰微信；
// 真正的微信发送/收读仍只由 OpenClaw(girl) 负责。
//
// 为什么要这层：不管靠她"自觉写标记"（会漏），或内部 message hook（拿不到触发源）。
// 类型化插件在 before_agent_run 能读到本次运行的 ctx.trigger：
//   "user"     → 她在回主人的一条新消息 → __REPLY__
//   "heartbeat"/"cron"/其它 → 她自己主动发 → __SELF__
// message_sent 不暴露 trigger、也不可靠带 runId，所以用 sessionKey 从刻度里反查。
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { appendFile } from "node:fs/promises";

const GIRL_SESSION_PREFIX = "agent:girl";            // 只关心 girl 会话
const FEED_PATH =
  "E:\\college_information\\girl\\girl_workspace\\memory\\send_feed.md";
const REPLY = "__REPLY__";   // 在回主人的一条新消息
const SELF = "__SELF__";     // 自己主动发

const pendingTrigger = new Map();  // sessionKey -> 本次运行的 trigger

async function record(kind) {
  try {
    await appendFile(FEED_PATH, kind + "\n", "utf8");
  } catch (err) {
    console.error("[send-feed] 写入失败:", err && err.message);
  }
}

function isGirl(sessionKey) {
  return typeof sessionKey === "string" && sessionKey.startsWith(GIRL_SESSION_PREFIX);
}

export default definePluginEntry({
  id: "send-feed",
  name: "SendFeed Hook",
  description: "按触发源把她的每一条真实发送机械记进 send_feed.md（回他/主动）",
  register(api) {
    const opts = { priority: 50 };

    // 每次运行开始：记下本次运行的触发源
    api.on("before_agent_run", (event, ctx) => {
      if (ctx && ctx.sessionKey && ctx.trigger) {
        pendingTrigger.set(ctx.sessionKey, ctx.trigger);
      }
    }, opts);

    // 她真发出消息且成功 → 用触发源分类写一行
    api.on("message_sent", async (event, ctx) => {
      if (!ctx || !isGirl(ctx.sessionKey)) return;
      if (!event || !event.success) return;
      const trigger = pendingTrigger.get(ctx.sessionKey);
      // 缺刻度的保险默认 → __SELF__：宁可多记一次主动，也不误判回他而错误解开未回闸
      await record(trigger === "user" ? REPLY : SELF);
    }, opts);

    // 运行结束：清掉该会话的触发源，防止串台/误判
    api.on("agent_end", (event, ctx) => {
      if (ctx && ctx.sessionKey) pendingTrigger.delete(ctx.sessionKey);
    }, opts);
  },
});
