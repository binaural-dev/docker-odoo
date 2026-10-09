#!/usr/bin/env bash
# sdd_opencode_cleanup.sh — reap stale SDD OpenCode jobs.
#
# Kills orphaned tmux sessions on the SDD socket and prunes stale job
# directories (src/.sdd/logs/jobs/*, overridable via SDD_LOG_ROOT) older
# than the TTL. metrics.jsonl lives one level up and is never touched here. Cheap and safe to run at the start of every
# sdd-lead Modo Delegación run — this repo has one job type and one workdir,
# so unlike swarm-forge's per-role watchdog there is nothing to reconcile
# beyond "is this job dir/session older than the TTL".
#
# Usage: bash sdd_opencode_cleanup.sh [--older-than <hours>] [--all]
#   --older-than <hours>  TTL in hours (default 6)
#   --all                 ignore TTL, reap everything (used in tests)

set -euo pipefail

TMUX_SOCKET="/tmp/sdd-tmux/sdd.sock"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDD_LOG_ROOT="${SDD_LOG_ROOT:-$REPO_ROOT/src/.sdd/logs}"
JOBS_DIR="$SDD_LOG_ROOT/jobs"
TTL_HOURS=6
REAP_ALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --older-than)
      TTL_HOURS="${2:?missing hours value for --older-than}"
      shift 2
      ;;
    --all)
      REAP_ALL=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

[[ -d "$JOBS_DIR" ]] || { echo '{"reaped_sessions":0,"reaped_dirs":0}'; exit 0; }

TTL_SECONDS=$(( TTL_HOURS * 3600 ))
ARCHIVE_DIR="$(dirname "$JOBS_DIR")/archive"
ARCHIVE_DAYS=30
[[ -d "$ARCHIVE_DIR" ]] && find "$ARCHIVE_DIR" -type f -mtime +"$ARCHIVE_DAYS" -delete 2>/dev/null || true
NOW=$(date +%s)

REAPED_SESSIONS=0
REAPED_DIRS=0

for job_dir in "$JOBS_DIR"/*/; do
  [[ -d "$job_dir" ]] || continue
  job_id="$(basename "$job_dir")"

  # A job whose tmux session died without a checkpoint stays "running" until someone polls it
  # (sdd-1791555935028 sat like that for hours). Flip it to orphaned here so the metric is emitted
  # and the reporter sees it; status.sh owns the transition and is idempotent.
  if [[ "$(cat "$job_dir/status" 2>/dev/null)" == "running" ]] && \
     ! tmux -S "$TMUX_SOCKET" has-session -t "$job_id" 2>/dev/null; then
    bash "$(dirname "$0")/sdd_opencode_status.sh" "$job_id" >/dev/null 2>&1 || true
  fi

  age=$(( NOW - $(stat -c '%Y' "$job_dir" 2>/dev/null || echo "$NOW") ))
  stale=0
  if [[ "$REAP_ALL" -eq 1 || "$age" -ge "$TTL_SECONDS" ]]; then
    stale=1
  fi

  if [[ "$stale" -eq 1 ]]; then
    if tmux -S "$TMUX_SOCKET" has-session -t "$job_id" 2>/dev/null; then
      tmux -S "$TMUX_SOCKET" kill-session -t "$job_id" 2>/dev/null || true
      REAPED_SESSIONS=$(( REAPED_SESSIONS + 1 ))
    fi
    # Keep the verdict evidence past the job-dir TTL: result.handoff (or the log tail) goes to archive/
    # and is pruned after ARCHIVE_DAYS. Without it, FAIL/orphaned jobs left no evidence after 6 h.
    mkdir -p "$ARCHIVE_DIR"
    if [[ -f "$job_dir/result.handoff" ]]; then
      cp "$job_dir/result.handoff" "$ARCHIVE_DIR/$job_id.handoff" 2>/dev/null || true
    elif [[ -f "$job_dir/output.log" ]]; then
      tail -n 60 "$job_dir/output.log" > "$ARCHIVE_DIR/$job_id.tail" 2>/dev/null || true
    fi
    rm -rf "$job_dir"
    REAPED_DIRS=$(( REAPED_DIRS + 1 ))
  fi
done

printf '{"reaped_sessions":%d,"reaped_dirs":%d,"ttl_hours":%d}\n' \
  "$REAPED_SESSIONS" "$REAPED_DIRS" "$TTL_HOURS"
