#!/usr/bin/env bash
# sdd_judge_event.sh — records the sdd-judge verdict for a delegated job in metrics.jsonl.
#
# Until now the judge's PASS/FAIL/NEEDS_HUMAN_INPUT only lived in the lead's conversation, so
# sdd-metrics-reporter could not measure the FAIL rate, iterations per job, or how often the judge disagrees with
# OpenCode's own report. Append-only, same file and event shape as sdd_opencode_run.sh.
#
# Usage: bash sdd_judge_event.sh <job_id> <PASS|FAIL|NEEDS_HUMAN_INPUT> <iteration> [reason...]
#   iteration: 1-based retry-loop round (R5 caps it at 3).
# Prints the appended JSON line. Exit 1 on bad arguments (nothing is written).

set -euo pipefail

JOB_ID="${1:-}"
VERDICT="${2:-}"
ITERATION="${3:-}"
shift 3 2>/dev/null || true
REASON="$*"

if [[ -z "$JOB_ID" || ! "$VERDICT" =~ ^(PASS|FAIL|NEEDS_HUMAN_INPUT)$ || ! "$ITERATION" =~ ^[0-9]+$ ]]; then
  echo "usage: sdd_judge_event.sh <job_id> <PASS|FAIL|NEEDS_HUMAN_INPUT> <iteration> [reason...]" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDD_LOG_ROOT="${SDD_LOG_ROOT:-$REPO_ROOT/src/.sdd/logs}"
METRICS_FILE="$SDD_LOG_ROOT/metrics.jsonl"
mkdir -p "$SDD_LOG_ROOT"

python3 - "$JOB_ID" "$VERDICT" "$ITERATION" "$REASON" <<'PY' | tee -a "$METRICS_FILE"
import datetime, json, sys
job, verdict, iteration, reason = sys.argv[1:]
print(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "job": job,
                  "event": "judge_verdict", "verdict": verdict, "iteration": int(iteration), "reason": reason[:300]}))
PY
