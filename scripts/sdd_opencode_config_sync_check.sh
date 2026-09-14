#!/usr/bin/env bash
# sdd_opencode_config_sync_check.sh — detects drift between the two OpenCode
# config files that must stay aligned for the SDD roles (per
# src/.opencode/skills/sdd-opencode-guardrails/SKILL.md, "Dos archivos de
# config, uno gana"): the project config `src/.opencode/opencode.json` (the
# one that actually applies inside this repo) and the user-global
# `~/.config/opencode/opencode.jsonc`. These drifted undetected for 5 roles
# (build/conductor/tester/plan/odoo-dev) until a manual audit on 2026-09-05 —
# this script replaces "remember to sync manually" with something that can
# actually be run (by a human, by sdd-metrics-reporter at report time, or as
# a pre-commit check) and exits non-zero when they disagree.
#
# Usage: bash sdd_opencode_config_sync_check.sh
# Exit 0: every agent role present in both files has the same `model`.
# Exit 1: at least one role's model differs, or is missing from one side —
#         details printed to stdout.
#
# Only compares `agent.<name>.model` — that's the field that has actually
# drifted in the past (per the guardrails skill's own history). Extend the
# python block below if another field needs the same treatment.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_CONFIG="${SDD_OPENCODE_LOCAL_CONFIG:-$REPO_ROOT/src/.opencode/opencode.json}"
GLOBAL_CONFIG="${SDD_OPENCODE_GLOBAL_CONFIG:-$HOME/.config/opencode/opencode.jsonc}"

if [[ ! -f "$LOCAL_CONFIG" ]]; then
  echo "error: local config not found at $LOCAL_CONFIG"
  exit 1
fi
if [[ ! -f "$GLOBAL_CONFIG" ]]; then
  echo "error: global config not found at $GLOBAL_CONFIG"
  exit 1
fi

python3 - "$LOCAL_CONFIG" "$GLOBAL_CONFIG" <<'PY'
import json
import sys


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas, respecting string
    literals (so a "https://..." value or a literal // inside a string isn't
    mistaken for a comment start)."""
    out = []
    i, n = 0, len(text)
    in_string = False
    escape = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    cleaned = "".join(out)
    # Trailing commas before a closing bracket/brace (valid in JSONC, not JSON).
    import re
    cleaned = re.sub(r",(\s*[\]}])", r"\1", cleaned)
    return cleaned


local_path, global_path = sys.argv[1], sys.argv[2]
local_cfg = json.load(open(local_path))
global_cfg = json.loads(strip_jsonc(open(global_path).read()))

local_agents = local_cfg.get("agent", {})
global_agents = global_cfg.get("agent", {})

# A role declared in only ONE of the two files is not necessarily a problem —
# a purely personal/global-only agent (never used inside this project) is a
# legitimate pattern. What actually broke before (5 roles, 2026-09-05) was a
# role declared in BOTH files with a DIFFERENT model — that's the real drift
# this check exists to catch, so only that case fails the run.
shared_roles = sorted(set(local_agents) & set(global_agents))
only_local = sorted(set(local_agents) - set(global_agents))
only_global = sorted(set(global_agents) - set(local_agents))

drift = []
for role in shared_roles:
    local_model = local_agents.get(role, {}).get("model")
    global_model = global_agents.get(role, {}).get("model")
    if local_model != global_model:
        drift.append((role, local_model, global_model))

if only_local:
    print(f"info: role(s) only in project config (not necessarily a problem): {', '.join(only_local)}")
if only_global:
    print(f"info: role(s) only in global config (not necessarily a problem): {', '.join(only_global)}")

if drift:
    print("DRIFT DETECTED: role(s) declared in BOTH configs with a different model:")
    for role, lm, gm in drift:
        print(f"  - agent.{role}.model: project={lm!r} global={gm!r}")
    print()
    print(f"project config: {local_path}")
    print(f"global config:  {global_path}")
    sys.exit(1)

print(f"ok: {len(shared_roles)} shared agent role(s) checked, no model drift between project and global config")
sys.exit(0)
PY
