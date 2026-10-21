#!/usr/bin/env bash
# sdd_judge_event.sh — records the sdd-judge verdict for a delegated job in metrics.jsonl.
#
# Until now the judge's PASS/FAIL/NEEDS_HUMAN_INPUT only lived in the lead's conversation, so
# sdd-metrics-reporter could not measure the FAIL rate, iterations per job, or how often the judge disagrees with
# OpenCode's own report. Append-only, same file and event shape as sdd_opencode_run.sh.
#
# Usage: bash sdd_judge_event.sh <job_id> <PASS|FAIL|NEEDS_HUMAN_INPUT> <iteration> <tree_sha> [reason...]
#   tree_sha: output of `bash scripts/sdd_tree_proof.sh <repo_dir>` — binds the verdict to the judged tree.
#   iteration: 1-based retry-loop round (R5 caps it at 3).
#   SDD_ERROR_CLASS (env, optional, FAIL only): infra|context|guardrail|spec|code|test|tooling|misread — recorded as
#   `error_class` so sdd_error_report.py can group repeated failures.
# Prints the appended JSON line. Exit 1 on bad arguments (nothing is written).

set -euo pipefail

JOB_ID="${1:-}"
VERDICT="${2:-}"
ITERATION="${3:-}"
TREE_SHA="${4:-}"
shift 4 2>/dev/null || true
REASON="$*"

if [[ -z "$JOB_ID" || ! "$VERDICT" =~ ^(PASS|FAIL|NEEDS_HUMAN_INPUT)$ || ! "$ITERATION" =~ ^[0-9]+$ || ! "$TREE_SHA" =~ ^[0-9a-f]{40,64}$ ]]; then
  echo "usage: sdd_judge_event.sh <job_id> <PASS|FAIL|NEEDS_HUMAN_INPUT> <iteration> <tree_sha> [reason...]" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDD_LOG_ROOT="${SDD_LOG_ROOT:-$REPO_ROOT/src/.sdd/logs}"
METRICS_FILE="$SDD_LOG_ROOT/metrics.jsonl"
mkdir -p "$SDD_LOG_ROOT"

SDD_ERROR_CLASS="${SDD_ERROR_CLASS:-}" python3 - "$JOB_ID" "$VERDICT" "$ITERATION" "$TREE_SHA" "$REASON" <<'PY' | tee -a "$METRICS_FILE"
import datetime, json, os, sys
CLASSES = ("infra", "context", "guardrail", "spec", "code", "test", "tooling", "misread")
job, verdict, iteration, tree_sha, reason = sys.argv[1:]
print(json.dumps({"v": 1, "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "job": job,
                  "event": "judge_verdict", "verdict": verdict, "iteration": int(iteration), "tree_sha": tree_sha, "reason": reason[:300],
                  **({"error_class": os.environ["SDD_ERROR_CLASS"]}
                     if verdict == "FAIL" and os.environ.get("SDD_ERROR_CLASS") in CLASSES else {})}))
PY
