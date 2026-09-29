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
#        bash sdd_opencode_run.sh "@<path-to-prompt-file>" [agent] [model] [cwd]
#   agent defaults to "sdd-lead"; cwd defaults to the repo's src/ directory.
#
# The "@<path>" form reads the prompt from a file instead of the positional
# argument. Prefer it whenever the caller is itself an LLM relaying this
# dispatch on someone else's behalf (e.g. sdd-opencode-runner, invoked via
# Task by sdd-lead): a long multi-paragraph prompt embedded directly in a
# relay's own tool call is something the relay model has to *retype*, and it
# has been observed to silently truncate/paraphrase it instead of reproducing
# it verbatim (confirmed 2026-09-05: a real dispatch's dispatch.handoff ended
# up containing only the Context{} block, with the entire task description
# after it dropped, no error surfaced anywhere). Writing the prompt to a
# scratch file first and passing "@<path>" means the relay only has to copy a
# short file path into its command — nothing left for it to paraphrase.

set -euo pipefail

RAW_PROMPT="${1:-}"
if [[ "$RAW_PROMPT" == @* ]]; then
  PROMPT_FILE="${RAW_PROMPT#@}"
  if [[ ! -f "$PROMPT_FILE" ]]; then
    printf '{"error":"prompt file not found: %s","status":"failed"}\n' "$PROMPT_FILE"
    exit 1
  fi
  PROMPT="$(cat "$PROMPT_FILE")"
else
  PROMPT="$RAW_PROMPT"
fi
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
# The tmux socket is fine to live in /tmp: it's only meaningful while the
# tmux server process is alive, which itself doesn't survive a reboot either.
# Job artifacts (dispatch/result handoffs, output.log, metrics) are the part
# that needs to survive a system restart to be worth anything for post-hoc
# analysis or the metrics reporter — /tmp/sdd-jobs was getting wiped on every
# host reset (2026-09-02 incidents), silently destroying the only record of
# what happened. SDD_LOG_ROOT is overridable for tests.
TMUX_SOCKET_DIR="/tmp/sdd-tmux"
TMUX_SOCKET="$TMUX_SOCKET_DIR/sdd.sock"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDD_LOG_ROOT="${SDD_LOG_ROOT:-$REPO_ROOT/src/.sdd/logs}"
JOBS_DIR="$SDD_LOG_ROOT/jobs"
LOG="$SDD_LOG_ROOT/sdd-opencode.log"
METRICS_FILE="$SDD_LOG_ROOT/metrics.jsonl"
mkdir -p "$TMUX_SOCKET_DIR" "$JOBS_DIR" "$SDD_LOG_ROOT"

CYAN='\033[38;5;87m'
DIM='\033[2m'
GREEN='\033[38;5;114m'
RED='\033[38;5;203m'
YELLOW='\033[38;5;221m'
RESET='\033[0m'

log() { printf '%s\n' "$1" >> "$LOG"; }

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Appends one JSON line to metrics.jsonl for the sdd-metrics-reporter agent.
# Fields are passed as key=value pairs; python3 gives safe JSON escaping when
# available, falling back to a naive (unescaped) line so metrics collection
# never blocks a dispatch even on a stripped-down environment.
append_metric() {
  local event="$1"; shift
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$JOB_ID" "$event" "$@" >> "$METRICS_FILE" 2>/dev/null <<'PY' || true
import datetime, json, sys
job, event, *rest = sys.argv[1:]
d = {"ts": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "job": job, "event": event}
for kv in rest:
    if "=" in kv:
        k, v = kv.split("=", 1)
        d[k] = v
print(json.dumps(d))
PY
  else
    local pairs="" kv
    for kv in "$@"; do pairs+=",\"${kv%%=*}\":\"${kv#*=}\""; done
    printf '{"ts":"%s","job":"%s","event":"%s"%s}\n' "$(now_iso)" "$JOB_ID" "$event" "$pairs" >> "$METRICS_FILE"
  fi
}

# Pulls a single-line "key: value" out of the prompt's Context{} block. Only
# handles single-line values (allowed_files is captured as its raw list text,
# e.g. "[models/*.py, views/*.xml]", not parsed into an array) — good enough
# for an audit trail, not meant to be a full SudoLang parser.
# Context{} values arrive as free text from an LLM-written prompt, and in
# practice callers wrap them in quotes (`repo: "custom/cadipa1/integra-addons"`)
# or append prose (`branch: 19.0 (rama principal, NO hagas checkout)`).
# Unnormalized, the quotes made the cwd/repo guardrail below reject ~33
# otherwise-valid dispatches (2026-09-16..22), and the prose ended up as
# literal cycle directory names under src/.sdd/logs/cycles/. Every field gets
# its surrounding quotes stripped; identifier fields (repo/branch/environment/
# odoo_version) are additionally cut at the first trailing comment.
IDENTIFIER_CONTEXT_FIELDS=" repo branch environment odoo_version "

extract_context_field() {
  local field="$1" value
  value="$(grep -m1 -E "^[[:space:]]*${field}:" <<<"$PROMPT" | sed -E "s/^[[:space:]]*${field}:[[:space:]]*//")"
  value="$(sed -E 's/[[:space:]]+$//' <<<"$value")"
  if [[ "$IDENTIFIER_CONTEXT_FIELDS" == *" $field "* ]]; then
    value="$(sed -E 's/[[:space:]]+(\(|#|—|--).*$//' <<<"$value")"
  fi
  value="$(sed -E "s/^[\"'\`](.*)[\"'\`]$/\1/" <<<"$value")"
  printf '%s' "$value"
}

# Model actually used for the dispatch: the explicit 3rd arg if given,
# otherwise what OpenCode resolves from src/.opencode/opencode.json
# (agent.<name>.model, then the top-level model). Only used for metrics —
# OC_ARGS still passes --model only when explicitly given.
resolve_model() {
  if [[ -n "$MODEL" ]]; then
    printf '%s' "$MODEL"
    return
  fi
  python3 - "$REPO_ROOT/src/.opencode/opencode.json" "$AGENT" 2>/dev/null <<'PY' || true
import json, sys
cfg = json.load(open(sys.argv[1]))
print((cfg.get("agent", {}).get(sys.argv[2], {}) or {}).get("model") or cfg.get("model") or "", end="")
PY
}

reject_dispatch() {
  local error_msg="$1"
  local job_id="sdd-$(date +%s%3N)"
  local job_dir="$JOBS_DIR/$job_id"
  mkdir -p "$job_dir"
  echo "failed" > "$job_dir/status"
  echo "1" > "$job_dir/exit_code"
  # A guardrail rejection (missing Context field, cwd/repo mismatch, duplicate
  # dispatch lock) used to leave zero trace in metrics.jsonl — the script
  # exited before the only append_metric call in the file (the "dispatch"
  # event, further down) ever ran. That undercounted the real failure rate:
  # sdd-metrics-reporter had no way to see how many dispatches never made it
  # past validation. JOB_ID is the global append_metric reads, so it's set
  # here even though this job never reaches the normal JOB_ID assignment.
  JOB_ID="$job_id"
  append_metric "rejected" "reason=$error_msg"
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

# --- branch must be a real git ref name ------------------------------------
# After normalization, anything still containing whitespace or parentheses is
# prose (e.g. "(ninguna — trabajar directo sobre el working tree)"), not a
# branch. It keys cycles/<branch>/ (read by sdd-judge) and the dispatch lock,
# so reject it instead of creating a directory named after a sentence.
DISPATCH_BRANCH_CHECK="$(extract_context_field branch)"
if [[ "$DISPATCH_BRANCH_CHECK" =~ [[:space:]\(\)] ]]; then
  DISPATCH_BRANCH_RAW="$(grep -m1 -E "^[[:space:]]*branch:" <<<"$PROMPT" | sed -E 's/^[[:space:]]*branch:[[:space:]]*//')"
  reject_dispatch "branch must be a git branch name or 'none', got '${DISPATCH_BRANCH_RAW}' — put instructions like 'do not checkout' in the prompt body, not in the Context branch field"
fi

# --- duplicate-dispatch lock ----------------------------------------------
# Observed in production (2026-09-12 23:39-23:40): 6 byte-identical dispatches
# of the same task fired within under a minute (a relay re-dispatching instead
# of waiting/polling for the already-running job — see sdd-opencode-delegate-
# agent's "sub-agente puede desobedecer" note). None of the 6 ever produced a
# result event; they just vanished from metrics.jsonl with no `orphaned`
# classification either. This lock closes that hole: a dispatch identical to
# one already in flight for the same repo/module/branch is rejected instead of
# silently racing it, and the rejection is now visible (see reject_dispatch's
# "rejected" metric event above).
hash_key() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  else
    cksum | cut -d' ' -f1
  fi
}

LOCK_DIR="$SDD_LOG_ROOT/locks"
mkdir -p "$LOCK_DIR"
DISPATCH_MODULE_EARLY="$(extract_context_field module)"
DISPATCH_BRANCH_EARLY="$(extract_context_field branch)"
LOCK_HASH="$(printf '%s' "${DISPATCH_REPO}|${DISPATCH_MODULE_EARLY}|${DISPATCH_BRANCH_EARLY}|${PROMPT}" | hash_key)"
LOCK_FILE="$LOCK_DIR/$LOCK_HASH.lock"
LOCK_WINDOW_S=90

if [[ -f "$LOCK_FILE" ]]; then
  existing_job="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  existing_status="$(cat "$JOBS_DIR/$existing_job/status" 2>/dev/null || true)"
  lock_mtime="$(stat -c %Y "$LOCK_FILE" 2>/dev/null || stat -f %m "$LOCK_FILE" 2>/dev/null || echo 0)"
  lock_age=$(( $(date +%s) - lock_mtime ))
  if [[ -n "$existing_job" ]] && \
     [[ "$existing_status" != "done" && "$existing_status" != "failed" && "$existing_status" != "orphaned" ]] && \
     (( lock_age < LOCK_WINDOW_S )); then
    reject_dispatch "duplicate dispatch of identical prompt (repo=${DISPATCH_REPO} module=${DISPATCH_MODULE_EARLY} branch=${DISPATCH_BRANCH_EARLY}) within ${LOCK_WINDOW_S}s of an in-flight job=${existing_job} (status=${existing_status:-unknown}) — wait/poll the existing job instead of re-dispatching"
  fi
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

# Claim the duplicate-dispatch lock now that this dispatch has passed every
# rejection check and is actually going to run — released on terminal status
# (done/failed/orphaned) either below (early failure paths) or inside
# INNER_CMD once opencode itself finishes.
echo "$JOB_ID" > "$LOCK_FILE"

OC_BIN="$(command -v opencode 2>/dev/null || true)"
if [[ -z "$OC_BIN" ]]; then
  log "$(printf "${RED}  ✗ job %s failed: opencode not found in PATH${RESET}" "$JOB_ID")"
  echo "failed" > "$STATUS_FILE"
  echo "127" > "$EXIT_FILE"
  write_result_handoff "failed" "127"
  rm -f "$LOCK_FILE"
  printf '{"job":"%s","dir":"%s","status":"failed","error":"opencode not found"}\n' "$JOB_ID" "$JOB_DIR"
  exit 1
fi

command -v tmux >/dev/null 2>&1 || {
  log "$(printf "${RED}  ✗ job %s failed: tmux not found in PATH${RESET}" "$JOB_ID")"
  echo "failed" > "$STATUS_FILE"
  echo "127" > "$EXIT_FILE"
  write_result_handoff "failed" "127"
  rm -f "$LOCK_FILE"
  printf '{"job":"%s","dir":"%s","status":"failed","error":"tmux not found"}\n' "$JOB_ID" "$JOB_DIR"
  exit 1
}

write_dispatch_handoff
echo "running" > "$STATUS_FILE"

# --- cumulative allowed_files across retry rounds of the same branch -------
# sdd-judge used to only ever see the LATEST dispatch's allowed_files, which
# produced a false SCOPE FAIL when a legitimate change spanned several retry
# rounds of the same cycle (TA-15107 round 3: two files from round 1, already
# evaluated on their merits, got flagged as scope violations in round 3
# because round 3's dispatch.handoff didn't re-list them) — costing a full
# wasted retry iteration. Rounds of the same cycle share a branch, so key the
# cumulative set by branch: each dispatch's allowed_files gets unioned in here
# instead of judge only ever reading the single latest dispatch.handoff.
CYCLE_BRANCH="$(extract_context_field branch)"
if [[ -n "$CYCLE_BRANCH" ]]; then
  CYCLE_DIR="$SDD_LOG_ROOT/cycles/$(printf '%s' "$CYCLE_BRANCH" | tr '/' '_')"
  mkdir -p "$CYCLE_DIR"
  CYCLE_ALLOWED_FILES="$CYCLE_DIR/allowed_files.txt"
  extract_context_field allowed_files >> "$CYCLE_ALLOWED_FILES"
  sort -u -o "$CYCLE_ALLOWED_FILES" "$CYCLE_ALLOWED_FILES"
  echo "$JOB_ID" >> "$CYCLE_DIR/jobs.txt"
fi

DISPATCH_MODULE="$(extract_context_field module)"
DISPATCH_BRANCH="$(extract_context_field branch)"
append_metric "dispatch" \
  "agent=$AGENT" "model=$(resolve_model)" "repo=$DISPATCH_REPO" "module=$DISPATCH_MODULE" \
  "environment=$DISPATCH_ENV" "branch=$DISPATCH_BRANCH"

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
_start=\$(date +%s)
"$OC_BIN" $OC_ARGS_Q 2>&1 | tee "$OUT"
ec=\${PIPESTATUS[0]}
_duration=\$(( \$(date +%s) - _start ))
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
echo "{\"ts\":\"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"job\":\"$JOB_ID\",\"event\":\"result\",\"status\":\"\$st\",\"exit_code\":\$ec,\"duration_s\":\$_duration}" >> "$METRICS_FILE"
rm -f "$LOCK_FILE"
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
