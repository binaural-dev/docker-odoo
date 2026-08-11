#!/usr/bin/env bash
# sdd_opencode_status.sh — non-blocking status check for a job dispatched by
# sdd_opencode_run.sh.
#
# Prints a single JSON line. When the job is done/failed, includes the
# result.handoff body. When still running, includes a tail of output.log.
# Cross-checks tmux directly: if the job dir still says "running" but the
# tmux session is gone, the job orphaned (crashed/killed) without writing its
# final status — reported as "orphaned" so the caller (sdd-lead) knows to
# retry instead of waiting forever.
#
# Usage: bash sdd_opencode_status.sh <job_id>

set -euo pipefail

JOB_ID="${1:-}"
if [[ -z "$JOB_ID" ]]; then
  printf '{"error":"no job_id","status":"failed"}\n'
  exit 1
fi

TMUX_SOCKET="/tmp/sdd-tmux/sdd.sock"
JOB_DIR="/tmp/sdd-jobs/$JOB_ID"

if [[ ! -d "$JOB_DIR" ]]; then
  printf '{"job":"%s","status":"unknown","error":"job dir not found"}\n' "$JOB_ID"
  exit 1
fi

STATUS_FILE="$JOB_DIR/status"
EXIT_FILE="$JOB_DIR/exit_code"
OUT="$JOB_DIR/output.log"
RESULT_FILE="$JOB_DIR/result.handoff"

STATUS="$(cat "$STATUS_FILE" 2>/dev/null || echo "unknown")"

session_alive() {
  tmux -S "$TMUX_SOCKET" has-session -t "$JOB_ID" 2>/dev/null
}

json_escape() {
  # Minimal JSON string escaping for embedding raw text as a JSON value.
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null \
    || sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g' | sed 's/^/"/;s/$/"/'
}

if [[ "$STATUS" == "running" ]] && ! session_alive; then
  # tmux session is gone but the job never wrote done/failed — it died
  # without a checkpoint (killed, crashed, host restart). Surface this
  # distinctly so sdd-lead retries instead of polling a dead job forever.
  echo "orphaned" > "$STATUS_FILE"
  STATUS="orphaned"
fi

case "$STATUS" in
  done|failed)
    EXIT_CODE="$(cat "$EXIT_FILE" 2>/dev/null || echo -1)"
    RESULT_BODY="$(cat "$RESULT_FILE" 2>/dev/null || echo "")"
    ESCAPED_RESULT="$(printf '%s' "$RESULT_BODY" | json_escape)"
    printf '{"job":"%s","dir":"%s","status":"%s","exit_code":%s,"result":%s}\n' \
      "$JOB_ID" "$JOB_DIR" "$STATUS" "$EXIT_CODE" "$ESCAPED_RESULT"
    ;;
  orphaned)
    TAIL_BODY="$(tail -n 40 "$OUT" 2>/dev/null || echo "")"
    ESCAPED_TAIL="$(printf '%s' "$TAIL_BODY" | json_escape)"
    printf '{"job":"%s","dir":"%s","status":"orphaned","tail":%s}\n' \
      "$JOB_ID" "$JOB_DIR" "$ESCAPED_TAIL"
    ;;
  running)
    TAIL_BODY="$(tail -n 20 "$OUT" 2>/dev/null || echo "")"
    ESCAPED_TAIL="$(printf '%s' "$TAIL_BODY" | json_escape)"
    printf '{"job":"%s","dir":"%s","status":"running","tail":%s}\n' \
      "$JOB_ID" "$JOB_DIR" "$ESCAPED_TAIL"
    ;;
  *)
    printf '{"job":"%s","dir":"%s","status":"unknown"}\n' "$JOB_ID" "$JOB_DIR"
    ;;
esac
