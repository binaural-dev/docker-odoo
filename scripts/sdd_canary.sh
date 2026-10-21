#!/usr/bin/env bash
# sdd_canary.sh — chain canary (F4, P1-7): checks that a finished job closed the whole chain with CANONICAL machine
# artifacts (files / runner-written log rows), never prose: dispatch.handoff, result.handoff with exit_code,
# dispatch+result rows in metrics.jsonl, and (optional) the expected artifact file. Exit 1 = chain broken: STOP,
# do not expand the matrix of rounds.
# Usage: bash sdd_canary.sh <job_id> [expected_artifact_path]
set -uo pipefail
JOB="${1:?usage: sdd_canary.sh <job_id> [expected_artifact]}"; ART="${2:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${SDD_LOG_ROOT:-$ROOT/src/.sdd/logs}"; D="$LOGS/jobs/$JOB"; bad=0
chk() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; bad=1; fi; }
chk "dispatch.handoff exists" "[[ -f $D/dispatch.handoff ]]"
chk "result.handoff exists" "[[ -f $D/result.handoff ]]"
chk "result.handoff has exit_code 0" "grep -qx 'exit_code: 0' $D/result.handoff 2>/dev/null"
chk "metrics: dispatch row" "grep -q '\"job\": *\"$JOB\".*\"event\": *\"dispatch\"' $LOGS/metrics.jsonl"
chk "metrics: result row" "grep -q '\"job\": *\"$JOB\".*\"event\": *\"result\"' $LOGS/metrics.jsonl"
[[ -n "$ART" ]] && chk "artifact $ART non-empty" "[[ -s $ART ]]"
exit $bad
