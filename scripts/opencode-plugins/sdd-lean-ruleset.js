// OpenCode plugin: appends scripts/lean-change.md to the system prompt of the agents listed in SDD_LEAN_AGENTS
// (default: sdd-builder) when SDD_LEAN_MODE=on (default: off). Also adds it to the compaction context.
// Loaded through the "plugin" key of scripts/sdd-guardrails.json (OPENCODE_CONFIG), so only SDD jobs get it.
// No network, no child processes, no global state file: the mode comes from the environment of the job only.
import fs from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const RULESET = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "lean-change.md")

const enabled = () => (process.env.SDD_LEAN_MODE || "off").trim().toLowerCase() === "on"
const targets = () => new Set((process.env.SDD_LEAN_AGENTS || "sdd-builder").split(",").map((s) => s.trim()).filter(Boolean))

// Read on every call (cheap, local) so a missing file just disables the injection instead of failing the job.
const text = () => {
  try {
    return fs.readFileSync(RULESET, "utf8").trim()
  } catch {
    return ""
  }
}

export const SddLeanRuleset = async () => {
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
