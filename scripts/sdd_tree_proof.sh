#!/usr/bin/env bash
# sdd_tree_proof.sh — content identity of a repo state, for binding judge verdicts to a tree (F1, P0-1).
#
# Prints the git tree object id of the WORKTREE (tracked + untracked, honouring .gitignore), computed through a
# scratch index so the real index is never touched. With --write also stores {head,tree,scope} in
# <git-dir>/sdd-proof. With --index prints the tree of the real index instead (what a commit would record).
#
# Usage: bash sdd_tree_proof.sh [--index|--write] [repo_dir]
set -euo pipefail

MODE="worktree"
case "${1:-}" in --index) MODE=index; shift ;; --write) MODE=write; shift ;; esac
REPO="${1:-.}"
cd "$REPO"
git rev-parse --git-dir >/dev/null

if [[ "$MODE" == index ]]; then git write-tree; exit 0; fi

SCRATCH="$(mktemp)"; trap 'rm -f "$SCRATCH"' EXIT
cp "$(git rev-parse --git-path index)" "$SCRATCH" 2>/dev/null || true
TREE="$(GIT_INDEX_FILE="$SCRATCH" bash -c 'git add -A >/dev/null 2>&1; git write-tree')"

if [[ "$MODE" == write ]]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  printf '{"head":"%s","tree":"%s","scope":"%s"}\n' "$(git rev-parse HEAD)" "$TREE" "$BRANCH" > "$(git rev-parse --git-path sdd-proof)"
fi
echo "$TREE"
