#!/usr/bin/env bash
# sdd_rehydrate.sh — bounded state block to re-read after a context compaction (F4, P1-6). Never parse a
# compaction summary as evidence: print paths + sha256 + last job state straight from disk instead.
# Usage: bash sdd_rehydrate.sh <module> [branch]
set -uo pipefail
MOD="${1:?usage: sdd_rehydrate.sh <module> [branch]}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${SDD_LOG_ROOT:-$ROOT/src/.sdd/logs}"
echo "module: $MOD"
for a in spec plan tasks qc-report; do
  f="$ROOT/src/specs/$MOD/$a.md"
  if [[ -f "$f" ]]; then echo "$a: src/specs/$MOD/$a.md sha256=$(sha256sum "$f" | cut -c1-16)"; else echo "$a: absent"; fi
done
# last dispatch of this module: job id, whether it has a result.handoff (no result = discarded, not no-op)
last="$(grep -l "^module: $MOD\$" "$LOGS"/jobs/*/dispatch.handoff 2>/dev/null | tail -1)"
if [[ -n "$last" ]]; then
  d="$(dirname "$last")"
  echo "last_job: $(basename "$d") status=$(cat "$d/status" 2>/dev/null || echo ?) result_handoff=$([[ -f $d/result.handoff ]] && echo yes || echo 'no (treat as discarded)')"
  grep -E "^(spec_sha256|branch):" "$last" | sed 's/^/  /'
  [[ -f "$d/result.handoff" ]] && grep -E "^(spec_sha256_end|spec_changed|exit_code):" "$d/result.handoff" | sed 's/^/  /'
else
  echo "last_job: none"
fi
n=$(grep -c "\"event\": *\"judge_verdict\"" "$LOGS/metrics.jsonl" 2>/dev/null); echo "verdicts: ${n:-0} judge_verdict rows in metrics.jsonl (all jobs)"
