// OpenCode plugin: runs scripts/sdd_odoo_cmd_guard.sh before every bash tool call and
// aborts the call when the command targets a real Odoo database (guard exit != 0).
// Loaded through the "plugin" key of scripts/sdd-guardrails.json (OPENCODE_CONFIG).
import { spawnSync } from "node:child_process"
import { fileURLToPath } from "node:url"
import path from "node:path"

const GUARD = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "sdd_odoo_cmd_guard.sh")

export const SddOdooGuard = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return
    const command = output.args?.command
    if (typeof command !== "string" || !command.includes("odoo")) return
    const res = spawnSync("bash", [GUARD, command], { encoding: "utf8" })
    if (res.status !== 0) {
      throw new Error(`sdd_odoo_cmd_guard: ${(res.stdout || res.stderr || "blocked").trim()}`)
    }
  },
})
