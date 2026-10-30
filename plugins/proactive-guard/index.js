// proactive-guard 插件：主动系统的机械计数器（P1 主菜的数据层）。
//
// 职责：把"她今天主动发了几条、他连续几次没理她的主动"记成状态文件，
// 供心跳 prompt 裁决。退让规则在 prompt 里，数据在这里。
//
// 钩子：before_agent_run 抓触发源，message_sent 按触发源分类，agent_end 清刻度。
// 本版带完整诊断日志（每个判断点都说话），定位 10.7 的钩子数据形状后可静音。

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
    console.log("[proactive-guard] recompute: 日志不存在，跳过");
    return;
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
    await writeFile(STATE_PATH, JSON.stringify(state, null, 2), "utf8");
    console.log(`[proactive-guard] 状态已更新: ${JSON.stringify(state)}`);
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
    console.log(
      `[proactive-guard] armed. prefix=${PREFIX}\n  log=${LOG_PATH}\n  state=${STATE_PATH}`
    );

    api.on("before_agent_run", (event, ctx) => {
      console.log(
        `[proactive-guard] before_agent_run: session=${ctx?.sessionKey} trigger=${ctx?.trigger}`
      );
      if (ctx && ctx.sessionKey && ctx.trigger) {
        pendingTrigger.set(ctx.sessionKey, ctx.trigger);
      }
    }, opts);

    api.on("message_sent", async (event, ctx) => {
      console.log(
        `[proactive-guard] message_sent 触发: session=${ctx?.sessionKey} success=${event?.success} ` +
        `eventKeys=[${event ? Object.keys(event).join(",") : "(无)"}] ` +
        `ctxKeys=[${ctx ? Object.keys(ctx).join(",") : "(无)"}]`
      );
      if (!ctx || !isGirl(ctx.sessionKey)) {
        console.log("[proactive-guard] 跳过：不是 girl 会话");
        return;
      }
      if (!event || !event.success) {
        console.log("[proactive-guard] 跳过：success 非 true");
        return;
      }
      const trigger = pendingTrigger.get(ctx.sessionKey);
      const kind = trigger === "user" ? REPLY : SELF;
      console.log(`[proactive-guard] 记录: ${kind} (trigger=${trigger ?? "未知→按SELF"})`);
      try {
        const dir = LOG_PATH.substring(0, LOG_PATH.lastIndexOf("\\"));
        await mkdir(dir, { recursive: true });
        await appendFile(LOG_PATH, `[${new Date().toISOString()}] ${kind}\n`, "utf8");
      } catch (err) {
        console.error("[proactive-guard] 日志写入失败:", err && err.message);
        return;
      }
      await recompute();
    }, opts);

    api.on("agent_end", (event, ctx) => {
      console.log(`[proactive-guard] agent_end: session=${ctx?.sessionKey}`);
      if (ctx && ctx.sessionKey) pendingTrigger.delete(ctx.sessionKey);
    }, opts);
  },
});
