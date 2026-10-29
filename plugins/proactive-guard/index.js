// proactive-guard 插件：主动系统的机械计数器（P1 主菜的数据层）。
//
// 职责只有一个：把"她今天主动发了几条、他连续几次没理她的主动"记成状态文件，
// 供心跳 prompt 在裁决"要不要主动开口"时读取。退让规则（每天 ≤2、连续 4 次不回
// 就收手）和情绪递进（unanswered 1-3 语气变化）的裁决在 prompt 里，数据在这里。
//
// 只用已验证的钩子（与 send-feed 同款）：before_agent_run 抓触发源，
// message_sent 按触发源分类（user→REPLY / 其它→SELF），agent_end 清刻度。
// 记录落在自己的日志文件（带时间戳，和 send_feed.md 互不干扰），状态落 JSON。

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";

const PREFIX = process.env.GIRL_SESSION_PREFIX || "agent:default";
const LOG_PATH =
  process.env.GIRL_PROACTIVE_LOG ||
  "D:\\girl-xiaoyu\\girl_workspace\\memory\\proactive_log.md";
const STATE_PATH =
  process.env.GIRL_PROACTIVE_STATE ||
  "D:\\girl-xiaoyu\\girl_workspace\\memory\\proactive_state.json";

const REPLY = "REPLY";
const SELF = "SELF";
const pendingTrigger = new Map(); // sessionKey -> 本次运行的触发源

function isGirl(sessionKey) {
  return typeof sessionKey === "string" && sessionKey.startsWith(PREFIX);
}

function today() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

async function recompute() {
  let lines = [];
  try {
    const text = await readFile(LOG_PATH, "utf8");
    lines = text.split("\n");
  } catch {
    return; // 日志还没有 → 无状态可算
  }
  const marks = [];
  for (const ln of lines) {
    const m = ln.match(/^\[([^\]]+)\]\s+(REPLY|SELF)\s*$/);
    if (m) marks.push({ ts: m[1], kind: m[2] });
  }
  const t = today();
  const selfToday = marks.filter((x) => x.kind === SELF && x.ts.slice(0, 10) === t).length;
  let unanswered = 0;
  for (let i = marks.length - 1; i >= 0; i--) {
    if (marks[i].kind === REPLY) break;
    if (marks[i].kind === SELF) unanswered++;
  }
  const lastSelf = [...marks].reverse().find((x) => x.kind === SELF);
  const state = {
    date: t,
    selfToday,
    unanswered,
    lastSelfAt: lastSelf ? lastSelf.ts : null,
    updatedAt: new Date().toISOString(),
  };
  try {
    await mkdir(LOG_PATH.substring(0, LOG_PATH.lastIndexOf("\\")), { recursive: true });
    await writeFile(STATE_PATH, JSON.stringify(state, null, 2), "utf8");
  } catch (err) {
    console.error("[proactive-guard] 状态写入失败:", err && err.message);
  }
}

export default definePluginEntry({
  id: "proactive-guard",
  name: "Proactive Guard",
  description:
    "主动系统机械计数：按触发源记她的每条真实发送（REPLY/SELF），维护 selfToday/unanswered 状态供心跳裁决",
  register(api) {
    const opts = { priority: 50 };

    api.on("before_agent_run", (event, ctx) => {
      if (ctx && ctx.sessionKey && ctx.trigger) {
        pendingTrigger.set(ctx.sessionKey, ctx.trigger);
      }
    }, opts);

    api.on("message_sent", async (event, ctx) => {
      if (!ctx || !isGirl(ctx.sessionKey)) return;
      if (!event || !event.success) return;
      const trigger = pendingTrigger.get(ctx.sessionKey);
      const kind = trigger === "user" ? REPLY : SELF; // 保险默认 SELF，宁可多记主动
      try {
        await mkdir(LOG_PATH.substring(0, LOG_PATH.lastIndexOf("\\")), { recursive: true });
        await appendFile(LOG_PATH, `[${new Date().toISOString()}] ${kind}\n`, "utf8");
      } catch (err) {
        console.error("[proactive-guard] 记录失败:", err && err.message);
        return;
      }
      await recompute();
    }, opts);

    api.on("agent_end", (event, ctx) => {
      if (ctx && ctx.sessionKey) pendingTrigger.delete(ctx.sessionKey);
    }, opts);
  },
});
