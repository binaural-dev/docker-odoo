#!/usr/bin/env bash
# sdd_opencode_run.sh — headless, non-blocking OpenCode dispatcher for the SDD
# delegation flow.
#
# Previous version ran `opencode run ... | while read line; do ...; done > $OUT`
# in the *foreground* of the caller's Bash tool call. That pipe is a direct
# child of the process the harness manages for the duration of that single
# tool call: once the call's timeout (or the subagent that issued it) ends,
# the pipe is torn down and `opencode` dies mid-pipeline with no checkpoint.
#
# This version launches `opencode` inside a detached tmux session instead.
# tmux's server is its own long-lived process, independent of whoever created
# the session — validated experimentally: a session created inside one
# subagent's Bash call stayed alive and query-able (`tmux list-sessions`) from
# a second, fully independent subagent with no shared context, both during
# and after the first subagent's own execution ended. That decouples the
# opencode job's lifetime from any single tool call, which is the actual fix
# for "opencode dies in background". Adapted from unclebob/swarm-forge's core
# pattern (tmux session as the process's "init"), without swarm-forge's daemon
# or per-role git-worktree topology — this repo has one job type, one workdir.
#
# This script now DISPATCHES ONLY — it returns almost immediately with
# status "running". Use sdd_opencode_status.sh <job_id> to poll for
# completion, and sdd_opencode_cleanup.sh to reap old jobs/sessions.
#
# Usage: bash sdd_opencode_run.sh "<prompt>" [agent] [model] [cwd]
#   agent defaults to "sdd-lead"; cwd defaults to the repo's src/ directory.

set -euo pipefail

PROMPT="${1:-}"
AGENT="${2:-sdd-lead}"
MODEL="${3:-}"
WORK_DIR="${4:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../src" && pwd)}"

if [[ -z "$PROMPT" ]]; then
  printf '{"error":"no prompt","status":"failed"}\n'
  exit 1
fi

TMUX_SOCKET_DIR="/tmp/sdd-tmux"
TMUX_SOCKET="$TMUX_SOCKET_DIR/sdd.sock"
JOBS_DIR="/tmp/sdd-jobs"
LOG_DIR="/tmp/swarm-code-logs"
LOG="$LOG_DIR/sdd-opencode.log"
mkdir -p "$TMUX_SOCKET_DIR" "$JOBS_DIR" "$LOG_DIR"

JOB_ID="sdd-$(date +%s%3N)"
JOB_DIR="$JOBS_DIR/$JOB_ID"
mkdir -p "$JOB_DIR"

OUT="$JOB_DIR/output.log"
STATUS_FILE="$JOB_DIR/status"
EXIT_FILE="$JOB_DIR/exit_code"
DISPATCH_FILE="$JOB_DIR/dispatch.handoff"
RESULT_FILE="$JOB_DIR/result.handoff"

CYAN='\033[38;5;87m'
DIM='\033[2m'
GREEN='\033[38;5;114m'
RED='\033[38;5;203m'
RESET='\033[0m'

log() { printf '%s\n' "$1" >> "$LOG"; }

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# --- swarm-forge-inspired typed handoff message: headers + blank line + body.
# Kept minimal on purpose: no daemon delivers these, the polling consumer
# (sdd-opencode-runner in status-check mode) just reads the job dir directly.
write_dispatch_handoff() {
  {
    echo "type: dispatch"
    echo "from: sdd-opencode-runner"
    echo "to: opencode"
    echo "job: $JOB_ID"
    echo "agent: $AGENT"
    [[ -n "$MODEL" ]] && echo "model: $MODEL"
    echo "cwd: $WORK_DIR"
    echo "priority: 50"
    echo "created_at: $(now_iso)"
    echo
    printf '%s\n' "$PROMPT"
  } > "$DISPATCH_FILE"
}

write_result_handoff() {
  local status="$1" exit_code="$2"
  local tail_lines
  tail_lines="$(tail -n 40 "$OUT" 2>/dev/null || true)"
  {
    echo "type: result"
    echo "from: opencode"
    echo "to: sdd-lead"
    echo "job: $JOB_ID"
    echo "status: $status"
    echo "exit_code: $exit_code"
    echo "completed_at: $(now_iso)"
    echo
    echo "output: $OUT"
    echo
    echo "--- tail (last 40 lines) ---"
    printf '%s\n' "$tail_lines"
  } > "$RESULT_FILE"
}

OC_BIN="$(command -v opencode 2>/dev/null || true)"
if [[ -z "$OC_BIN" ]]; then
  log "$(printf "${RED}  ✗ job %s failed: opencode not found in PATH${RESET}" "$JOB_ID")"
  echo "failed" > "$STATUS_FILE"
  echo "127" > "$EXIT_FILE"
  write_result_handoff "failed" "127"
  printf '{"job":"%s","dir":"%s","status":"failed","error":"opencode not found"}\n' "$JOB_ID" "$JOB_DIR"
  exit 1
fi

command -v tmux >/dev/null 2>&1 || {
  log "$(printf "${RED}  ✗ job %s failed: tmux not found in PATH${RESET}" "$JOB_ID")"
  echo "failed" > "$STATUS_FILE"
  echo "127" > "$EXIT_FILE"
  write_result_handoff "failed" "127"
  printf '{"job":"%s","dir":"%s","status":"failed","error":"tmux not found"}\n' "$JOB_ID" "$JOB_DIR"
  exit 1
}

write_dispatch_handoff
echo "running" > "$STATUS_FILE"

OC_ARGS=("run" "--agent" "$AGENT" "--auto")
[[ -n "$MODEL" ]] && OC_ARGS+=("--model" "$MODEL")
[[ -n "$WORK_DIR" && -d "$WORK_DIR" ]] && OC_ARGS+=("--dir" "$WORK_DIR")
OC_ARGS+=("$PROMPT")
# --auto only resolves "ask" rules for this headless run (no TTY to prompt);
# explicit "deny" rules in each agent's permission block (see
# src/.opencode/agents/*.md) are still enforced regardless of --auto.
# User confirmed this tradeoff explicitly (2026-08-05).

# Build the in-tmux command as a single quoted string: run opencode, capture
# its own exit code, then write status/exit_code/result.handoff — all inside
# the detached session so it survives regardless of what happens to the shell
# that launched tmux.
printf -v OC_ARGS_Q '%q ' "${OC_ARGS[@]}"
INNER_CMD=$(cat <<EOF
"$OC_BIN" $OC_ARGS_Q > "$OUT" 2>&1
ec=\$?
echo "\$ec" > "$EXIT_FILE"
if [[ "\$ec" -eq 0 ]]; then
  st=done
else
  st=failed
fi
echo "\$st" > "$STATUS_FILE"
tail_body="\$(tail -n 40 "$OUT" 2>/dev/null || true)"
{
  echo "type: result"
  echo "from: opencode"
  echo "to: sdd-lead"
  echo "job: $JOB_ID"
  echo "status: \$st"
  echo "exit_code: \$ec"
  echo "completed_at: \$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo
  echo "output: $OUT"
  echo
  echo "--- tail (last 40 lines) ---"
  printf '%s\n' "\$tail_body"
} > "$RESULT_FILE"
EOF
)

log ""
log "$(printf "${CYAN}  ⚡ job %s dispatched to tmux (agent: %s)${RESET}" "$JOB_ID" "$AGENT")"
[[ -n "$MODEL" ]] && log "$(printf "${DIM}     model: %s${RESET}" "$MODEL")"
log "$(printf "${DIM}     dir: %s${RESET}" "$WORK_DIR")"
log "$(printf "${DIM}     job_dir: %s${RESET}" "$JOB_DIR")"
log "$(printf "${DIM}     task: %s${RESET}" "$(echo "$PROMPT" | head -c 120)")"

tmux -S "$TMUX_SOCKET" new-session -d -s "$JOB_ID" bash -c "$INNER_CMD"

log "$(printf "${GREEN}  → job %s running in tmux session %s (socket %s)${RESET}" "$JOB_ID" "$JOB_ID" "$TMUX_SOCKET")"

printf '{"job":"%s","dir":"%s","session":"%s","socket":"%s","status":"running"}\n' \
  "$JOB_ID" "$JOB_DIR" "$JOB_ID" "$TMUX_SOCKET"
