// proactive-guard v0.3：主动系统的机械计数器（P1 数据层）。
//
// 10.7 实测结论（2026-10-31）：
//   - before_agent_run ✅（带 sessionKey + trigger）
//   - llm_output ✅（带 runId + assistantTexts 回复全文 + usage）
//   - message_sent ❌ 对 napcat 通道投递不触发
//   - agent_end 先于最后一轮 llm_output 派发 → 提交动作必须挂在 llm_output 上
//
// 记账规则：llm_output 到达且输出非静默（非 HEARTBEAT_OK）→ 立即按触发源分类记账，
// 同一回合（runId）只记一次。状态文件供心跳 prompt 裁决（每天≤2、连续4次不回硬停）。

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
const pendingTrigger = new Map();   // sessionKey -> 本回合触发源
const lastCommittedRun = new Map(); // sessionKey -> 已记账的 runId（回合内去重）

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

async function recompute() {
  let lines = [];
  try {
    const text = await readFile(LOG_PATH, "utf8");
    lines = text.split("\n");
  } catch {
    console.log("[proactive-guard] recompute: log file missing, skip");
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
    console.log(`[proactive-guard] state updated: selfToday=${selfToday} unanswered=${unanswered}`);
  } catch (err) {
    console.error("[proactive-guard] state write failed:", err && err.message);
  }
}

async function record(kind) {
  try {
    const dir = LOG_PATH.substring(0, LOG_PATH.lastIndexOf("\\"));
    await mkdir(dir, { recursive: true });
    await appendFile(LOG_PATH, `[${new Date().toISOString()}] ${kind}\n`, "utf8");
  } catch (err) {
    console.error("[proactive-guard] log write failed:", err && err.message);
    return;
  }
  await recompute();
}

export default definePluginEntry({
  id: "proactive-guard",
  name: "Proactive Guard",
  description:
    "主动系统机械计数：llm_output 到达即按触发源分类记账（runId 去重），维护 selfToday/unanswered 状态供心跳裁决",
  register(api) {
    const opts = { priority: 50 };
    console.log(
      `[proactive-guard] armed. prefix=${PREFIX}\n  log=${LOG_PATH}\n  state=${STATE_PATH}`
    );

    api.on("before_agent_run", (event, ctx) => {
      console.log(`[proactive-guard] before_agent_run: session=${ctx?.sessionKey} trigger=${ctx?.trigger}`);
      if (ctx && ctx.sessionKey) {
        pendingTrigger.set(ctx.sessionKey, ctx.trigger);
      }
    }, opts);

    api.on("llm_output", (event, ctx) => {
      if (!ctx || !isGirl(ctx.sessionKey)) return;
      const runId = event?.runId || "";
      const output = (event?.assistantTexts || []).join(" ").trim();
      if (!output || isSilence(output)) {
        console.log(`[proactive-guard] llm_output: silence (${output.length} chars), skip`);
        return;
      }
      if (runId && lastCommittedRun.get(ctx.sessionKey) === runId) {
        console.log(`[proactive-guard] llm_output: run ${runId.slice(0, 8)} already committed, skip`);
        return;
      }
      if (runId) lastCommittedRun.set(ctx.sessionKey, runId);
      const trigger = pendingTrigger.get(ctx.sessionKey);
      const kind = trigger === "user" ? REPLY : SELF;
      console.log(
        `[proactive-guard] commit: ${kind} ${output.length} chars (trigger=${trigger ?? "?"}, runId=${runId.slice(0, 8)})`
      );
      record(kind).catch((err) =>
        console.error("[proactive-guard] record failed:", err && err.message)
      );
    }, opts);

    api.on("agent_end", (event, ctx) => {
      console.log(`[proactive-guard] agent_end: session=${ctx?.sessionKey}`);
      if (ctx && ctx.sessionKey) pendingTrigger.delete(ctx.sessionKey);
    }, opts);
  },
});
