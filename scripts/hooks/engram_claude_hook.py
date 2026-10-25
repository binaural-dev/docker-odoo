#!/usr/bin/env python3
"""Claude Code hook for the Engram memory layer: SessionStart, SessionEnd and SubagentStop.

SessionStart (startup, resume, clear, compact): registers the Claude session in Engram and returns a short
`additionalContext` with the recent memory (`engram context --all`, capped in bytes) and the session id that every
write must pass as `session_id`. Re-running on `compact` re-injects the same context after compaction.
SessionEnd: closes the session with `mem_session_end` (no summary: the agent writes it with mem_session_finalize).
SubagentStop: passive capture of the closing message of a write-capable subagent (redacted, capped in bytes).
Read-only subagents (sdd-judge, sdd-pm, sdd-qc) are never captured.

Fail-open: any error exits 0 with no output, so a broken memory never blocks a Claude session.
Local only: talks to the stdio MCP of the local engram binary and to its CLI, never to a network port.
"""

import json
import os
import subprocess
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sdd_memory_capture import save_observation  # noqa: E402
from sdd_memory_common import EngramMcp, EngramMcpError, ascii_keywords, engram_env, find_engram_binary, redact  # noqa: E402

CONTEXT_MAX_BYTES = int(os.environ.get("SDD_MEMORY_CONTEXT_BYTES", "3000"))
SUBAGENT_MAX_BYTES = int(os.environ.get("SDD_MEMORY_SUBAGENT_BYTES", "1500"))
# Plan decision 5: only these subagents may write. The read-only ones never reach Engram from the hook either.
WRITE_AGENTS = ("sdd-lead", "sdd-spec", "sdd-architect", "sdd-builder")


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


def subagent_observation(event):
    """(topic_key, title, content) to keep from a finished write-capable subagent, or None. Pure: no I/O."""
    agent = event.get("agent_type", "")
    agent_id = event.get("agent_id", "")
    if agent not in WRITE_AGENTS or not agent_id:
        return None
    clean, _ = redact(event.get("last_assistant_message") or "")
    clean = clean.encode("utf-8")[:SUBAGENT_MAX_BYTES].decode("utf-8", errors="ignore").strip()
    if not clean:
        return None
    content = f"{clean}\nkeywords: {ascii_keywords(clean, agent)}"
    return f"subagente/{agent}/{agent_id}", f"Cierre de {agent}", content


def subagent_stop(event):
    observation = subagent_observation(event)
    if observation is None:
        return None
    topic_key, title, content = observation
    # save_observation prints its own status line; the hook's stdout is reserved for its JSON output.
    with redirect_stdout(sys.stderr):
        save_observation(topic_key, title, content, cwd=event.get("cwd") or os.getcwd(), label="subagent")
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
        elif name == "SubagentStop":
            subagent_stop(event)
    except Exception:  # noqa: BLE001 - fail-open by design, see module docstring
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
