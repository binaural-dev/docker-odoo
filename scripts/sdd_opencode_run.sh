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
# WORK_DIR defaults to the whole src/ workspace only as a fallback for ad-hoc
# calls. Callers dispatching a scoped SDD task (sdd-lead) MUST pass the
# repo/module-scoped path explicitly here, e.g. "src/integra-addons-19.0" —
# not the bare src/ default — so OpenCode's --dir (and therefore its file
# tree/edit surface) is narrowed to the declared repo, on top of the
# engine-level odoo-*.0/enterprise-*.0 deny rules that already apply.
WORK_DIR="${4:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../src" && pwd)}"

if [[ -z "$PROMPT" ]]; then
  printf '{"error":"no prompt","status":"failed"}\n'
  exit 1
fi

# --- required Context{} fields ------------------------------------------
# The dispatch prompt must embed a SudoLang-style `Context { ... }` block
# declaring the task's scope explicitly, e.g.:
#   Context {
#     environment: qa-consultoria-integra-19
#     odoo_version: 19.0
#     repo: integra-addons-19.0
#     module: binaural_farming
#     branch: feat_task-123_add-thing
#     allowed_files: [models/*.py, views/*.xml]
#   }
# This is checked with plain grep, not a real block-scoped parser (per
# design: cheap enough to run on every dispatch, good enough to catch the
# "forgot to declare scope" case that made OpenCode's operating context a
# free-text convention instead of an enforced contract).
TMUX_SOCKET_DIR="/tmp/sdd-tmux"
TMUX_SOCKET="$TMUX_SOCKET_DIR/sdd.sock"
JOBS_DIR="/tmp/sdd-jobs"
LOG_DIR="/tmp/swarm-code-logs"
LOG="$LOG_DIR/sdd-opencode.log"
mkdir -p "$TMUX_SOCKET_DIR" "$JOBS_DIR" "$LOG_DIR"

CYAN='\033[38;5;87m'
DIM='\033[2m'
GREEN='\033[38;5;114m'
RED='\033[38;5;203m'
YELLOW='\033[38;5;221m'
RESET='\033[0m'

log() { printf '%s\n' "$1" >> "$LOG"; }

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Pulls a single-line "key: value" out of the prompt's Context{} block. Only
# handles single-line values (allowed_files is captured as its raw list text,
# e.g. "[models/*.py, views/*.xml]", not parsed into an array) — good enough
# for an audit trail, not meant to be a full SudoLang parser.
extract_context_field() {
  local field="$1"
  grep -m1 -E "^[[:space:]]*${field}:" <<<"$PROMPT" | sed -E "s/^[[:space:]]*${field}:[[:space:]]*//"
}

reject_dispatch() {
  local error_msg="$1"
  local job_id="sdd-$(date +%s%3N)"
  local job_dir="$JOBS_DIR/$job_id"
  mkdir -p "$job_dir"
  echo "failed" > "$job_dir/status"
  echo "1" > "$job_dir/exit_code"
  printf '{"error":"%s","job":"%s","dir":"%s","status":"failed"}\n' "$error_msg" "$job_id" "$job_dir"
  exit 1
}

REQUIRED_CONTEXT_FIELDS=(environment odoo_version repo module branch allowed_files)
missing_fields=()
for field in "${REQUIRED_CONTEXT_FIELDS[@]}"; do
  if ! grep -qE "^[[:space:]]*${field}:" <<<"$PROMPT"; then
    missing_fields+=("$field")
  fi
done

if [[ ${#missing_fields[@]} -gt 0 ]]; then
  missing_csv="$(IFS=,; echo "${missing_fields[*]}")"
  reject_dispatch "missing required context fields: ${missing_csv}"
fi

# --- cwd must match the declared repo -------------------------------------
# --dir/WORK_DIR is the real technical boundary of what OpenCode can see/edit
# (the engine-level odoo-*.0/enterprise-*.0 deny rules use paths relative to
# it). Context{}'s `repo:` field is otherwise just a human-readable string —
# nothing enforced it matched the actual sandbox until now. If the caller
# forgot to narrow WORK_DIR (4th arg) to the declared repo and it's still
# pointing at the broad src/ fallback (or any dir that doesn't contain the
# repo name as a path segment), reject before tmux/opencode ever launches:
# this is exactly the "OpenCode ends up with visibility into other clients'
# repos" failure mode this guardrail closes.
DISPATCH_REPO="$(extract_context_field repo)"
if [[ -n "$DISPATCH_REPO" ]] && [[ "$WORK_DIR" != *"$DISPATCH_REPO"* ]]; then
  reject_dispatch "cwd does not match declared repo: WORK_DIR='${WORK_DIR}' repo='${DISPATCH_REPO}' — pass the repo-scoped path as the 4th arg (e.g. src/${DISPATCH_REPO}), not the src/ default"
fi

# --- environment must never be pattern-guessed -----------------------------
# A `-tests` suffix on `environment` is only a real convention for modules
# from the shared pools (integra-addons-*/odoo-venezuela-*/third-party-
# addons-*), which version independently of any client repo and carry their
# version in the directory name itself. Client-specific environments
# (src/custom/<client>/) vary in name and must NEVER be guessed by that
# pattern. This is a soft signal, not a hard block — `environment` is still
# a free-text field someone explicitly declared; the point is to leave an
# audit trail if it looks like the `-tests` convention was copied out of
# habit instead of the real client environment being declared.
DISPATCH_ENV="$(extract_context_field environment)"
if [[ "$DISPATCH_ENV" == *-tests ]] && \
   [[ "$DISPATCH_REPO" != integra-addons* ]] && \
   [[ "$DISPATCH_REPO" != odoo-venezuela* ]] && \
   [[ "$DISPATCH_REPO" != third-party-addons* ]]; then
  log "$(printf "${YELLOW}  ⚠ environment '%s' ends in -tests but repo '%s' is not a shared pool (integra-addons-*/odoo-venezuela-*/third-party-addons-*) — verify this wasn't guessed by pattern instead of declared for the actual client${RESET}" "$DISPATCH_ENV" "$DISPATCH_REPO")"
fi

JOB_ID="sdd-$(date +%s%3N)"
JOB_DIR="$JOBS_DIR/$JOB_ID"
mkdir -p "$JOB_DIR"

OUT="$JOB_DIR/output.log"
STATUS_FILE="$JOB_DIR/status"
EXIT_FILE="$JOB_DIR/exit_code"
DISPATCH_FILE="$JOB_DIR/dispatch.handoff"
RESULT_FILE="$JOB_DIR/result.handoff"

# --- swarm-forge-inspired typed handoff message: headers + blank line + body.
# Kept minimal on purpose: no daemon delivers these, the polling consumer
# (sdd-opencode-runner in status-check mode) just reads the job dir directly.
write_dispatch_handoff() {
  local branch allowed_files repo module
  branch="$(extract_context_field branch)"
  allowed_files="$(extract_context_field allowed_files)"
  repo="$(extract_context_field repo)"
  module="$(extract_context_field module)"
  {
    echo "type: dispatch"
    echo "from: sdd-opencode-runner"
    echo "to: opencode"
    echo "job: $JOB_ID"
    echo "agent: $AGENT"
    [[ -n "$MODEL" ]] && echo "model: $MODEL"
    echo "cwd: $WORK_DIR"
    echo "repo: $repo"
    echo "module: $module"
    echo "branch: $branch"
    echo "allowed_files: $allowed_files"
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
# piped through tee (not "> \$OUT 2>&1") so the output is visible live in the
# tmux pane itself, not just captured to the log file — otherwise a terminal
# window attached via sdd_opencode_view.sh shows nothing until the session
# ends. PIPESTATUS[0] recovers opencode's own exit code past the pipe.
"$OC_BIN" $OC_ARGS_Q 2>&1 | tee "$OUT"
ec=\${PIPESTATUS[0]}
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

# Opt-in only: opening an OS terminal window is a visual convenience for
# interactive use, not something headless/CI dispatches should trigger by
# default. See scripts/sdd_opencode_view.sh for the terminal-emulator
# autodetection/override (SDD_TMUX_TERMINAL) it uses.
if [[ "${SDD_TMUX_AUTO_VIEW:-}" == "1" ]]; then
  VIEW_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sdd_opencode_view.sh"
  if [[ -x "$VIEW_SCRIPT" ]]; then
    view_result="$(bash "$VIEW_SCRIPT" "$JOB_ID" 2>/dev/null || true)"
    log "$(printf "${DIM}     view: %s${RESET}" "$view_result")"
  fi
fi

printf '{"job":"%s","dir":"%s","session":"%s","socket":"%s","status":"running"}\n' \
  "$JOB_ID" "$JOB_DIR" "$JOB_ID" "$TMUX_SOCKET"
