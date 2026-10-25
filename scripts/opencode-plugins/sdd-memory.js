// OpenCode plugin: appends scripts/memory-protocol.md to the system prompt of the editing SDD agents listed in
// SDD_MEMORY_AGENTS (default: sdd-spec,sdd-architect,sdd-pm,sdd-builder) when SDD_MEMORY_MODE=on (default: off).
// Also adds it to the compaction context. Loaded through the "plugin" key of scripts/sdd-guardrails.json.
// Orchestrators, judges and the runner never get it (NEVER below), whatever SDD_MEMORY_AGENTS says: they return
// structured output and must keep their prefix stable (sudolang rule injected-rulesets).
// Fail-open: a missing protocol file disables the injection instead of failing the job.
// No network, no child processes, no global state file: the mode comes from the environment of the job only.
import fs from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const PROTOCOL = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "memory-protocol.md")
const NEVER = new Set(["sdd-lead", "sdd-judge", "sdd-qc", "sdd-opencode-runner"])

const enabled = () => (process.env.SDD_MEMORY_MODE || "off").trim().toLowerCase() === "on"
const targets = () =>
  new Set(
    (process.env.SDD_MEMORY_AGENTS || "sdd-spec,sdd-architect,sdd-pm,sdd-builder")
      .split(",")
      .map((s) => s.trim())
      .filter((a) => a && !NEVER.has(a)),
  )

// Read on every call (cheap, local) so a missing file just disables the injection instead of failing the job.
const text = () => {
  try {
    return fs.readFileSync(PROTOCOL, "utf8").trim()
  } catch {
    return ""
  }
}

export const SddMemory = async () => {
  // chat.message carries the agent; system.transform only carries the sessionID, so remember which session is whose.
  const agentBySession = new Map()
  return {
    "chat.message": async (input) => {
      if (input.sessionID && input.agent) agentBySession.set(input.sessionID, input.agent)
    },
    "experimental.chat.system.transform": async (input, output) => {
      if (!enabled() || !targets().has(agentBySession.get(input.sessionID))) return
      const body = text()
      if (body) output.system.push(body)
    },
    "experimental.session.compacting": async (input, output) => {
      if (!enabled() || !targets().has(agentBySession.get(input.sessionID))) return
      const body = text()
      if (body) output.context.push(body)
    },
  }
}
