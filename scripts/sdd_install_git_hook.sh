#!/usr/bin/env bash
# sdd_install_git_hook.sh — installs a pre-commit hook that runs sdd_verdict_gate.sh in <repo_dir>.
# Never overwrites: aborts if core.hooksPath is set or a pre-commit hook already exists.
# Usage: bash sdd_install_git_hook.sh <repo_dir>
set -euo pipefail
REPO="${1:?usage: sdd_install_git_hook.sh <repo_dir>}"
GATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sdd_verdict_gate.sh"
cd "$REPO"
HP="$(git config --get core.hooksPath || true)"
[[ -z "$HP" ]] || { echo "core.hooksPath is already $HP; add 'bash $GATE \"\$PWD\"' to its pre-commit manually" >&2; exit 1; }
HOOK="$(git rev-parse --git-path hooks/pre-commit)"
[[ ! -e "$HOOK" ]] || { echo "$HOOK already exists; not overwriting" >&2; exit 1; }
printf '#!/usr/bin/env bash\nexec bash "%s" "$(git rev-parse --show-toplevel)"\n' "$GATE" > "$HOOK"
chmod +x "$HOOK"; echo "installed $HOOK"
