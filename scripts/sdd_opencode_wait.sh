#!/usr/bin/env bash
# sdd_opencode_wait.sh — bounded low-cost wait for a job dispatched by
# sdd_opencode_run.sh, using a single Bash-tool call instead of many.
#
# Loops internally (sleep + status check) inside one process instead of
# forcing the caller to spawn a fresh Task(sdd-opencode-runner) subagent per
# poll. Delegates the actual status read to sdd_opencode_status.sh on every
# iteration so the orphaned/done/failed detection logic (tmux liveness
# cross-check) lives in exactly one place. Stops as soon as the job reaches a
# terminal state, or when max_seconds is exhausted (still "running").
#
# Usage: bash sdd_opencode_wait.sh <job_id> [max_seconds=480] [poll_interval=15]
#
# Prints the same JSON shape as sdd_opencode_status.sh, plus a "polls" field
# counting how many status reads this invocation performed (so the caller can
# track real elapsed coverage instead of a heuristic attempt count).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

JOB_ID="${1:-}"
MAX_SECONDS="${2:-480}"
POLL_INTERVAL="${3:-15}"

if [[ -z "$JOB_ID" ]]; then
  printf '{"error":"no job_id","status":"failed"}\n'
  exit 1
fi

# Beat before the first read: right after dispatch the job dir can take a
# moment to appear — an immediate check can otherwise silently read a
# leftover previous job_id's state (see AGENTS.md rule 172).
sleep 2

ELAPSED=0
POLLS=0
LAST_LINE=""

while true; do
  LAST_LINE="$(bash "$SCRIPT_DIR/sdd_opencode_status.sh" "$JOB_ID" || true)"
  POLLS=$((POLLS + 1))

  STATUS="$(printf '%s' "$LAST_LINE" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status","unknown"))' 2>/dev/null || echo "unknown")"

  case "$STATUS" in
    done|failed|orphaned)
      break
      ;;
  esac

  if (( ELAPSED >= MAX_SECONDS )); then
    break
  fi

  sleep "$POLL_INTERVAL"
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

# Re-emit the last status line with "polls" appended (still one JSON object,
# minimal string surgery to avoid depending on python3 for the happy path).
if printf '%s' "$LAST_LINE" | python3 -c 'import json,sys; d=json.load(sys.stdin); d["polls"]='"$POLLS"'; print(json.dumps(d))' 2>/dev/null; then
  :
else
  # python3 unavailable or LAST_LINE malformed — fall back to raw line plus
  # a separate polls marker so the caller still gets a poll count.
  printf '%s\n{"polls":%s}\n' "$LAST_LINE" "$POLLS"
fi
