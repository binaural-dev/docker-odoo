#!/usr/bin/env python3
"""Claude Code hook for the Engram memory layer: SessionStart and SessionEnd.

SessionStart (startup, resume, clear, compact): registers the Claude session in Engram and returns a short
`additionalContext` with the recent memory (`engram context --all`, capped in bytes) and the session id that every
write must pass as `session_id`. Re-running on `compact` re-injects the same context after compaction.
SessionEnd: closes the session with `mem_session_end` (no summary: the agent writes it with mem_session_finalize).

Fail-open: any error exits 0 with no output, so a broken memory never blocks a Claude session.
Local only: talks to the stdio MCP of the local engram binary and to its CLI, never to a network port.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sdd_memory_common import EngramMcp, EngramMcpError, engram_env, find_engram_binary  # noqa: E402

CONTEXT_MAX_BYTES = int(os.environ.get("SDD_MEMORY_CONTEXT_BYTES", "3000"))


def recent_context(binary):
    """Output of `engram context --all`, cut to CONTEXT_MAX_BYTES on a character boundary."""
    proc = subprocess.run(
        [binary, "context", "--all"],
        env=engram_env(),
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.encode("utf-8")[:CONTEXT_MAX_BYTES].decode("utf-8", errors="ignore").strip()


def session_start(binary, session_id, cwd):
    client = EngramMcp(binary, cwd=cwd)
    try:
        try:
            client.call("mem_session_start", {"id": session_id, "directory": cwd})
        except EngramMcpError as exc:
            # Already registered (resume or compact): keep going with the same session.
            print(f"engram hook: session already registered ({exc})", file=sys.stderr)
    finally:
        client.close()

    context = recent_context(binary)
    text = (
        f"Memoria Engram (local). session_id de esta sesión: {session_id}. "
        "Pásalo como session_id en cada mem_save y mem_session_finalize.\n"
    )
    if context:
        text += "\n" + context
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}


def session_end(binary, session_id, cwd):
    client = EngramMcp(binary, cwd=cwd)
    try:
        try:
            client.call("mem_session_end", {"id": session_id})
        except EngramMcpError as exc:
            print(f"engram hook: session already ended ({exc})", file=sys.stderr)
    finally:
        client.close()
    return None


def main(stdin=sys.stdin, stdout=sys.stdout):
    try:
        event = json.load(stdin)
    except (ValueError, OSError):
        return 0
    try:
        name = event.get("hook_event_name", "")
        session_id = event.get("session_id", "")
        cwd = event.get("cwd") or os.getcwd()
        binary = find_engram_binary()
        if not session_id or not os.path.exists(binary):
            return 0
        if name == "SessionStart":
            output = session_start(binary, session_id, cwd)
            stdout.write(json.dumps(output, ensure_ascii=False))
        elif name == "SessionEnd":
            session_end(binary, session_id, cwd)
    except Exception:  # noqa: BLE001 - fail-open by design, see module docstring
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
