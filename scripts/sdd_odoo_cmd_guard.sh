#!/usr/bin/env bash
# sdd_odoo_cmd_guard.sh — runtime validator closing the guardrail gap
# documented in src/.opencode/skills/sdd-opencode-guardrails/SKILL.md,
# section "OpenCode corrió -i/-u directo contra la BD real del cliente en vez
# de usar ./odoo test": the static deny-list glob only covers `docker
# exec*psql*`, not `docker exec ... odoo -d <db> -i/-u ...` — a real incident
# (countryclub, 2026-09-12) ran the odoo binary's -i/-u flags directly against
# a real client database instead of a disposable copy. A per-client deny glob
# (`docker exec*odoo*-d countryclub*`) is a point patch that has to be
# hand-extended for every client; this script is the durable fix the skill's
# own "seguimiento técnico pendiente" note called for: it cross-checks the
# `-d`/`--database` argument against the REAL instance/database names in
# instances.json at run time, not a static per-client pattern.
#
# Usage: bash sdd_odoo_cmd_guard.sh "<command line to validate>"
# Exit 0 + "ok: ..." on stdout  -> command may proceed.
# Exit 1 + "reject: ..." on stdout -> command touches a real instance's
#   database via the odoo binary's -d/--database flag and must be blocked.
#
# This is a standalone check, meant to be invoked as a pre-tool guard (e.g.
# from an OpenCode hook, or manually before approving an `ask`-gated bash
# command) — it does not itself intercept anything. It only judges commands
# that invoke the `odoo` binary with -d/--database; it deliberately does NOT
# touch `psql` (already covered by the existing `docker exec*psql*` deny) or
# any command that doesn't reference a database at all.

set -euo pipefail

CMD="${1:-}"
if [[ -z "$CMD" ]]; then
  echo "no command given"
  exit 1
fi

# Only commands invoking the odoo binary against a specific database via
# -d/--database matter here — anything else (docker exec ... python3 -m
# coverage, git commands, etc.) is out of scope for this guard.
if ! grep -qE '(^|[[:space:]/])odoo([[:space:]].*)?[[:space:]](-d|--database)[[:space:]=]' <<<"$CMD"; then
  echo "ok: not an odoo -d/--database invocation, out of scope for this guard"
  exit 0
fi

DB_NAME="$(grep -oE '(-d|--database)[[:space:]=]+[^[:space:]]+' <<<"$CMD" | head -1 \
  | sed -E "s/^(-d|--database)[[:space:]=]+//; s/^[\"']//; s/[\"']\$//")"

if [[ -z "$DB_NAME" ]]; then
  echo "ok: could not extract a -d/--database value, letting other guardrails handle it"
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTANCES_JSON="${SDD_INSTANCES_JSON:-$REPO_ROOT/instances.json}"

if [[ ! -f "$INSTANCES_JSON" ]]; then
  echo "warn: instances.json not found at $INSTANCES_JSON — cannot verify, rejecting to be safe"
  exit 1
fi

python3 - "$INSTANCES_JSON" "$DB_NAME" <<'PY'
import json
import sys

path, db = sys.argv[1], sys.argv[2]
data = json.load(open(path))
instances = data.get("instances", {})

# EXACT match only, deliberately not a prefix match: a disposable copy named
# e.g. "countryclub-copy-test-1789397" (the protocol sdd-opencode-guardrails
# itself documents as the correct way to test — create a NEW db by copy, with
# a distinguishing suffix, test against that, drop it after) legitimately
# starts with a protected name's prefix. Prefix-matching would reject that
# safe, correct usage along with the unsafe one — the actual incident this
# guard closes was an EXACT match against the real instance's own db name.
protected = set()
for name, cfg in instances.items():
    # "*-tests" instances exist specifically to be targeted directly (shared
    # pools' own throwaway test databases) — not protected.
    if name.lower().endswith("-tests"):
        continue
    protected.add(name.lower())
    db_filter = (cfg.get("overwrite_odoo_config") or {}).get("db_filter")
    if db_filter:
        # db_filter is an anchored regex like ^countryclub$ or
        # ^cadipa1\-dev1\-tests$ — strip anchors/escapes to recover the
        # literal name it matches.
        literal = db_filter.strip("^$").replace("\\-", "-").replace("\\.", ".")
        if not literal.lower().endswith("-tests"):
            protected.add(literal.lower())

# Known real databases that exist on the shared cluster but aren't declared
# as their own instances.json entry (e.g. ad hoc staging/read-replica clones
# of a real instance) — carried over from the static denylist this guard
# replaces, since instances.json alone can't derive them. Extend here if a
# similar case is found for another client.
KNOWN_UNREGISTERED_REAL_DBS = {"countryclub-stg", "countryclub-rls"}
protected |= KNOWN_UNREGISTERED_REAL_DBS

db_lower = db.lower()
if db_lower in protected:
    print(
        f"reject: -d {db} is a real instance/database name in instances.json (or a known "
        f"unregistered real staging/replica db) — never run odoo -i/-u/--stop-after-init "
        f"directly against a real instance's database; create a NEW disposable database "
        f"(e.g. a copy with a distinguishing timestamp suffix, per sdd-opencode-guardrails' "
        f"documented protocol) and test against that, or use ./odoo test instead."
    )
    sys.exit(1)

print(f"ok: {db} does not match any real instance/database name in instances.json")
sys.exit(0)
PY
