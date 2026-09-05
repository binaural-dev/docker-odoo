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
NOW=$(date +%s)

REAPED_SESSIONS=0
REAPED_DIRS=0

for job_dir in "$JOBS_DIR"/*/; do
  [[ -d "$job_dir" ]] || continue
  job_id="$(basename "$job_dir")"

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
    rm -rf "$job_dir"
    REAPED_DIRS=$(( REAPED_DIRS + 1 ))
  fi
done

printf '{"reaped_sessions":%d,"reaped_dirs":%d,"ttl_hours":%d}\n' \
  "$REAPED_SESSIONS" "$REAPED_DIRS" "$TTL_HOURS"
