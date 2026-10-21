#!/usr/bin/env python3
"""sdd_tool_guard.py — Claude Code PreToolUse hook (F2, P0-2): runtime parity with OpenCode's guardrails.

Single source of truth: scripts/sdd-guardrails.json (same deny catalog injected into OpenCode via OPENCODE_CONFIG).
Reads the hook JSON on stdin; exit 2 + stderr blocks the tool call. Everything is local (no network).

Modes (env SDD_GUARD_MODE, default "advisory" for the commit/push gate only, per plan R2/R3):
  - commit/push (`git commit*`, `git push*`): blocked unless authorised by SDD_COMMIT_AUTHORIZED=1 in Claude's
    environment or a fresh token file `.git/sdd-commit-authorized` (human: `! touch .git/sdd-commit-authorized`,
    valid 10 min). In advisory mode the discrepancy is only logged; SDD_GUARD_MODE=enforce blocks it.
  - every other deny rule (psql, core/enterprise edits, rm -rf, --force, ...): always enforced.
Every deny/advisory is appended to src/.sdd/logs/metrics.jsonl (event guard_check, v:1).
"""
import datetime, fnmatch, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT_RULES = {"git commit*", "git push*"}
TOKEN_TTL = 600


def log(**kw):
    try:
        path = os.path.join(os.environ.get("SDD_LOG_ROOT", os.path.join(ROOT, "src/.sdd/logs")), "metrics.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        kw.update(v=1, event="guard_check", ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        with open(path, "a") as f:
            f.write(json.dumps(kw) + "\n")
    except OSError:
        pass


def authorised():
    if os.environ.get("SDD_COMMIT_AUTHORIZED") == "1":
        return True
    tok = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", ROOT), ".git", "sdd-commit-authorized")
    try:
        return time.time() - os.path.getmtime(tok) < TOKEN_TTL
    except OSError:
        return False


def main():
    data = json.load(sys.stdin)
    tool, args = data.get("tool_name", ""), data.get("tool_input", {}) or {}
    cat = json.load(open(os.path.join(ROOT, "scripts/sdd-guardrails.json"))).get("permission", {})
    mode = os.environ.get("SDD_GUARD_MODE", "advisory")
    hit = None
    if tool == "Bash":
        # a command may chain several: judge each segment on its own
        for seg in re.split(r"&&|\|\||;|\||\n", args.get("command", "")):
            seg = seg.strip()
            for pat, action in cat.get("bash", {}).items():
                if action == "deny" and fnmatch.fnmatchcase(seg, pat):
                    hit = (pat, seg)
                    break
            if hit:
                break
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = os.path.abspath(args.get("file_path") or args.get("notebook_path") or "")
        for pat, action in cat.get("edit", {}).items():
            core = pat.strip("*/")
            if action == "deny" and f"/{core}/" in path + "/":
                hit = (pat, path)
                break
    if not hit:
        return 0
    pat, subject = hit
    if pat in COMMIT_RULES:
        if authorised():
            log(tool=tool, rule=pat, result="authorized")
            return 0
        if mode != "enforce":
            log(tool=tool, rule=pat, result="advisory", subject=subject[:200])
            print(f"sdd_tool_guard (advisory): '{pat}' needs human commit authorization (Gate 6)", file=sys.stderr)
            return 0
    log(tool=tool, rule=pat, result="deny", subject=subject[:200])
    print(f"sdd_tool_guard: blocked by rule '{pat}' (scripts/sdd-guardrails.json): {subject[:160]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
