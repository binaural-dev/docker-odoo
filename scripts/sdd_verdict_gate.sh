#!/usr/bin/env bash
# sdd_verdict_gate.sh — pre-commit gate (F1, P0-1): the staged tree must be the tree a judge PASSed, and the staged
# files must stay inside the cycle's allowed_files. Checks (a) judge_verdict PASS with tree_sha == index tree,
# (b) staged paths ⊆ cycles/<branch>/allowed_files.txt (skipped when that file does not exist).
#
# SDD_GATE_MODE=advisory (default): logs a gate_check event to metrics.jsonl, never blocks.
# SDD_GATE_MODE=enforce: exit 1 on violation.  SDD_GATE_SKIP=1: bypass (logged).
# Usage: bash sdd_verdict_gate.sh [repo_dir]
set -uo pipefail

REPO="${1:-.}"; cd "$REPO"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDD_LOG_ROOT="${SDD_LOG_ROOT:-$SCRIPT_DIR/../src/.sdd/logs}"
METRICS="$SDD_LOG_ROOT/metrics.jsonl"
MODE="${SDD_GATE_MODE:-advisory}"

python3 - "$MODE" "$METRICS" "$SDD_LOG_ROOT" "${SDD_GATE_SKIP:-0}" <<'PY'
import datetime, fnmatch, json, os, subprocess, sys
mode, metrics, root, skip = sys.argv[1:]
def git(*a): return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
idx, branch = git("write-tree"), git("rev-parse", "--abbrev-ref", "HEAD")
staged = [p for p in git("diff", "--cached", "--name-only", "-z", "--no-renames").split("\0") if p]
problems = []
if not staged:
    sys.exit(0)
ok = False
try:
    for line in open(metrics):
        try: d = json.loads(line)
        except ValueError: continue
        if d.get("event") == "judge_verdict" and d.get("verdict") == "PASS" and d.get("tree_sha") == idx:
            ok = True
except OSError:
    pass
if not ok:
    problems.append(f"no judge_verdict PASS bound to staged tree {idx[:12]}")
allowed_f = os.path.join(root, "cycles", branch.replace("/", "_"), "allowed_files.txt")
if os.path.exists(allowed_f):
    pats = [l.strip() for l in open(allowed_f) if l.strip()]
    out = [p for p in staged if not any(fnmatch.fnmatch(p, g) or fnmatch.fnmatch(os.path.basename(p), g) or p.startswith(g.rstrip("*")) for g in pats)]
    if out:
        problems.append("staged files outside allowed_files: " + ", ".join(out[:8]))
result = "skipped" if skip == "1" else ("pass" if not problems else ("block" if mode == "enforce" else "advisory"))
try:
    with open(metrics, "a") as f:
        f.write(json.dumps({"v": 1, "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": "gate_check", "branch": branch, "tree_sha": idx, "result": result, "reason": "; ".join(problems)[:300]}) + "\n")
except OSError:
    pass
if problems and skip != "1":
    print(("BLOCKED" if mode == "enforce" else "WARNING (advisory)") + " sdd_verdict_gate: " + "; ".join(problems), file=sys.stderr)
    sys.exit(1 if mode == "enforce" else 0)
PY
