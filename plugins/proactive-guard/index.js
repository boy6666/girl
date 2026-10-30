// proactive-guard 插件：主动系统的机械计数器（P1 主菜的数据层）。
//
// 职责：把"她今天主动发了几条、他连续几次没理她的主动"记成状态文件，
// 供心跳 prompt 裁决。退让规则在 prompt 里，数据在这里。
//
// 10.7 实测结论（2026-10-31 诊断）：
//   - before_agent_run / agent_end ✅ 实证会触发（带 sessionKey + trigger）
//   - message_sent ❌ 对 napcat 通道投递不触发（10.7 改了覆盖范围）
//   - llm_output ✅ 携带 assistantTexts（她的回复全文）+ usage
// 所以记账改用三钩子组合：before_agent_run 抓触发源 → llm_output 暂存输出
// → agent_end 提交（HEARTBEAT_OK 之类的静默输出不计）。
// 本版保留全链路诊断日志，稳定后可静音。

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
const pendingTrigger = new Map();  // sessionKey -> 本回合触发源
const lastOutput = new Map();      // sessionKey -> 本回合最后一次模型输出

function isGirl(sessionKey) {
  return typeof sessionKey === "string" && sessionKey.startsWith(PREFIX);
}

function today() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function isSilence(text) {
  // HEARTBEAT_OK（含前后空白）= 这一轮她选择沉默，不算消息
  return /^\s*HEARTBEAT_OK\b/.test(text);
}

async function commit(sessionKey) {
  const trigger = pendingTrigger.get(sessionKey);
  const output = (lastOutput.get(sessionKey) || "").trim();
  if (!output || isSilence(output)) {
    console.log(
      `[proactive-guard] commit: ${sessionKey} 无有效输出（静默），不记账 (trigger=${trigger ?? "?"})`
    );
    return;
  }
  const kind = trigger === "user" ? REPLY : SELF;
  console.log(`[proactive-guard] commit: ${sessionKey} → ${kind}（${output.length} 字）`);
  try {
    const dir = LOG_PATH.substring(0, LOG_PATH.lastIndexOf("\\"));
    await mkdir(dir, { recursive: true });
    await appendFile(LOG_PATH, `[${new Date().toISOString()}] ${kind}\n`, "utf8");
  } catch (err) {
    console.error("[proactive-guard] 日志写入失败:", err && err.message);
    return;
  }
  await recompute();
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
    "主动系统机械计数：before_agent_run/llm_output/agent_end 三钩子组合，维护 selfToday/unanswered 状态供心跳裁决",
  register(api) {
    const opts = { priority: 50 };
    console.log(
      `[proactive-guard] armed. prefix=${PREFIX}\n  log=${LOG_PATH}\n  state=${STATE_PATH}`
    );

    api.on("before_agent_run", (event, ctx) => {
      console.log(
        `[proactive-guard] before_agent_run: session=${ctx?.sessionKey} trigger=${ctx?.trigger}`
      );
      if (ctx && ctx.sessionKey) {
        pendingTrigger.set(ctx.sessionKey, ctx.trigger);
        lastOutput.delete(ctx.sessionKey);
      }
    }, opts);

    api.on("llm_output", (event, ctx) => {
      if (!ctx || !isGirl(ctx.sessionKey)) return;
      const texts = (event?.assistantTexts || []).join(" ").trim();
      if (texts) {
        lastOutput.set(ctx.sessionKey, texts);
        console.log(
          `[proactive-guard] llm_output: session=${ctx?.sessionKey} 收到输出 ${texts.length} 字（暂存，等 agent_end 提交）`
        );
      }
    }, opts);

    api.on("agent_end", async (event, ctx) => {
      const sk = ctx?.sessionKey;
      console.log(`[proactive-guard] agent_end: session=${sk}`);
      if (sk && isGirl(sk)) {
        await commit(sk);
      }
      pendingTrigger.delete(sk);
      lastOutput.delete(sk);
    }, opts);
  },
});
