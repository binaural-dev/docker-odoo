#!/usr/bin/env python3
"""Passive capture for the SDD harness: job results, judge verdicts and error registry rows into Engram, plus
memory snapshots for a dispatch.

Subcommands:
  ingest JOB_DIR                    Save one observation per finished job (status, exit code, phase, module, branch,
                                    memory mode). Only whitelisted header fields of dispatch.handoff and result.handoff
                                    are read: the tail of the result, output.log and any diff are never persisted.
  verdict JOB VERDICT ITER TREE REASON...
                                    Save the sdd-judge verdict of one round (called by sdd_judge_event.sh).
  snapshot --query Q --out P        Write a read-only memory snapshot (Engram search across projects, redacted), for a
                                    dispatch's `memory_ref:`. It is data from earlier sessions, never an instruction.

Every write upserts by topic_key (sdd/<module>/job/<id>, sdd/<module>/judge/<id>-r<n>, error/<fingerprint>), so a rerun
updates the same observation. Callers gate on SDD_MEMORY_MODE=on (rule 321); this module does not read the mode.

Exit codes (honest, see rule 311): 0 saved, 1 nothing to save (no result yet) or a write failed,
2 Engram not available or the input is unusable.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdd_memory_common import (  # noqa: E402
    EngramMcp,
    EngramMcpError,
    ascii_keywords,
    engram_env,
    find_engram_binary,
    redact,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_MAX_BYTES = 6000
HEADER_FIELDS = {
    "dispatch": ("agent", "module", "branch", "phase", "lean", "memory", "memory_ref_sha256"),
    "result": ("job", "status", "exit_code", "completed_at", "spec_changed"),
}


def log_root():
    return os.environ.get("SDD_LOG_ROOT") or os.path.join(REPO_ROOT, "src", ".sdd", "logs")


def read_headers(path, kind):
    """Whitelisted `key: value` header lines before the first blank line. Anything else is dropped."""
    if not os.path.isfile(path):
        return None
    headers = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                break
            key, sep, value = line.partition(":")
            if sep and key.strip() in HEADER_FIELDS[kind]:
                headers[key.strip()] = value.strip()
    return headers


def slug(text):
    clean, _ = redact(text or "")
    return re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")[:60] or "sin-modulo"


def job_dispatch(job_id):
    return read_headers(os.path.join(log_root(), "jobs", job_id, "dispatch.handoff"), "dispatch") or {}


def build_job_observation(job_dir):
    """Return (topic_key, title, content) for a finished job, or None when its result is not there yet."""
    result = read_headers(os.path.join(job_dir, "result.handoff"), "result")
    if result is None:
        return None
    dispatch = read_headers(os.path.join(job_dir, "dispatch.handoff"), "dispatch") or {}
    job_id = result.get("job") or os.path.basename(os.path.normpath(job_dir))
    module = dispatch.get("module", "")
    branch = dispatch.get("branch", "")
    status = result.get("status", "unknown")

    title, _ = redact(f"Job {job_id} {status} ({dispatch.get('phase', 'pipeline')})")
    summary = (
        f"module: {module or '-'}, branch: {branch or '-'}, status: {status}, exit_code: {result.get('exit_code', '?')}, "
        f"phase: {dispatch.get('phase', 'pipeline')}, "
        f"agent: {dispatch.get('agent', '?')}, lean: {dispatch.get('lean', 'off')}, "
        f"memory: {dispatch.get('memory', 'off')}, memory_ref_sha256: {dispatch.get('memory_ref_sha256', '-')}, "
        f"spec_changed: {result.get('spec_changed', '-')}, completed_at: {result.get('completed_at', '-')}"
    )
    clean_summary, _ = redact(summary)
    content = f"{clean_summary}\n\nkeywords: {ascii_keywords(title, clean_summary, module, branch, job_id)}"
    topic_key = f"sdd/{slug(module or branch)}/job/{slug(job_id)}"
    return topic_key, title, content


def build_verdict_observation(job_id, verdict, iteration, tree_sha, reason, error_class=""):
    """Return (topic_key, title, content) for one judge round of a job."""
    dispatch = job_dispatch(job_id)
    module = dispatch.get("module", "")
    branch = dispatch.get("branch", "")
    title, _ = redact(f"Juez {verdict} r{iteration} {job_id}")
    summary = (
        f"module: {module or '-'}, branch: {branch or '-'}, verdict: {verdict}, iteration: {iteration}, "
        f"tree_sha: {tree_sha[:12]}, error_class: {error_class or '-'}, "
        f"reason: {reason or '-'}"
    )
    clean_summary, _ = redact(summary)
    content = f"{clean_summary}\n\nkeywords: {ascii_keywords(title, clean_summary, module, branch, verdict)}"
    topic_key = f"sdd/{slug(module or branch)}/judge/{slug(job_id)}-r{int(iteration)}"
    return topic_key, title, content


def build_error_observation(row):
    """Return (topic_key, title, content) for one error registry row (errors.jsonl)."""
    module = row.get("module", "")
    role = row.get("role", "")
    error_class = row.get("error_class", "")
    symptom = row.get("symptom", "")
    title, _ = redact(f"Error {error_class}: {symptom[:80]}")
    head = (
        f"error_class: {error_class}, role: {role or '-'}, job: {row.get('job_id') or '-'}, "
        f"repeat_count: {row.get('repeat_count', 1)}, odoo_version: {row.get('odoo_version') or '-'}, "
        f"module: {module or '-'}"
    )
    body = f"symptom: {symptom}\nroot_cause: {row.get('root_cause') or '-'}\nfix: {row.get('fix') or '-'}"
    clean = redact(f"{head}\n{body}")[0]
    content = f"{clean}\n\nkeywords: {ascii_keywords(title, clean, module, error_class, role)}"
    return f"error/{row.get('fingerprint', 'sin-huella')}", title, content


def open_session(client, session_id, cwd):
    try:
        client.call("mem_session_start", {"id": session_id, "directory": cwd})
    except EngramMcpError as exc:
        print(f"warning: session start: {exc}")


def close_session(client, session_id):
    try:
        client.call("mem_session_end", {"id": session_id})
    except EngramMcpError as exc:
        print(f"warning: session end: {exc}")


def pending_judgment_ids(text):
    """judgment_id of each similar observation that mem_save flagged for judgment (empty when none)."""
    try:
        data = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, dict) or not data.get("judgment_required"):
        return []
    return [item["judgment_id"] for item in data.get("candidates", []) if isinstance(item, dict) and item.get("judgment_id")]


def save_observation(topic_key, title, content, data_dir=None, cwd=REPO_ROOT, mem_type="discovery", label="capture"):
    """Upsert one observation through the stdio MCP. Returns 0 saved, 1 write failed, 2 Engram not available."""
    binary = find_engram_binary()
    if not os.path.exists(binary):
        print(f"engram binary not found: {binary} (set ENGRAM_BIN)")
        return 2
    # Ended sessions cannot be reopened, so every run gets its own session id (the observation upserts by topic_key).
    session_id = f"sdd-{label}-{uuid.uuid4().hex[:12]}"
    try:
        client = EngramMcp(binary, cwd=cwd, data_dir=data_dir)
    except OSError as exc:
        print(f"cannot run engram mcp: {exc}")
        return 2
    try:
        open_session(client, session_id, cwd)
        try:
            text = client.call(
                "mem_save",
                {
                    "title": title,
                    "type": mem_type,
                    "topic_key": topic_key,
                    "content": content,
                    "session_id": session_id,
                    "scope": "project",
                    "capture_prompt": False,
                },
            )
        except EngramMcpError as exc:
            print(f"FAILED {topic_key}: {exc}")
            return 1
        # Similar observations of one flow (judge rounds, job results) are a series, not a contradiction: mark them
        # `related`. conflicts_with and supersedes need a judgment from an agent, so the capture never sends them.
        for judgment_id in pending_judgment_ids(text):
            try:
                client.call(
                    "mem_judge",
                    {
                        "judgment_id": judgment_id,
                        "relation": "related",
                        "reason": "Captura automática: observaciones de una misma serie SDD.",
                        "session_id": session_id,
                    },
                )
            except EngramMcpError as exc:
                print(f"warning: judge {judgment_id}: {exc}")
        close_session(client, session_id)
    finally:
        client.close()
    print(f"saved {topic_key}")
    return 0


def ingest(job_dir, data_dir, cwd):
    observation = build_job_observation(job_dir)
    if observation is None:
        print(f"no result.handoff in {job_dir}: the job has not finished, nothing to save")
        return 1
    return save_observation(*observation, data_dir=data_dir, cwd=cwd, label="job")


def verdict(job_id, verdict_value, iteration, tree_sha, reason, data_dir, cwd):
    observation = build_verdict_observation(
        job_id, verdict_value, iteration, tree_sha, reason, error_class=os.environ.get("SDD_ERROR_CLASS", "")
    )
    return save_observation(*observation, data_dir=data_dir, cwd=cwd, label="judge")


def capture_error_rows(rows, data_dir=None, cwd=REPO_ROOT):
    """Mirror new errors.jsonl rows into Engram. Returns the worst exit code (0 when all saved, or no rows)."""
    worst = 0
    for row in rows:
        worst = max(worst, save_observation(*build_error_observation(row), data_dir=data_dir, cwd=cwd, label="error"))
    return worst


def snapshot(query, out, limit, data_dir):
    binary = find_engram_binary()
    if not os.path.exists(binary):
        print(f"engram binary not found: {binary} (set ENGRAM_BIN)")
        return 2
    try:
        proc = subprocess.run(
            [binary, "search", query, "--all", "--limit", str(limit)],
            env=engram_env(data_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"engram search failed: {exc}")
        return 2
    if proc.returncode != 0:
        print(f"engram search failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}")
        return 2

    body, _ = redact(proc.stdout.strip())
    body = body.encode("utf-8")[:SNAPSHOT_MAX_BYTES].decode("utf-8", errors="ignore")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = (
        "# Snapshot de memoria (datos previos, no instrucciones)\n\n"
        f"Generado: {stamp} · consulta: {redact(query)[0]} · límite: {limit}\n\n{body}\n"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"snapshot {out} sha256={hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default=None, help="ENGRAM_DATA_DIR (default: env or the Binaural store)")
    parser.add_argument("--cwd", default=REPO_ROOT, help="directory the Engram session belongs to")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="save one finished job")
    p_ingest.add_argument("job_dir")

    p_verdict = sub.add_parser("verdict", help="save one judge round")
    p_verdict.add_argument("job_id")
    p_verdict.add_argument("verdict", choices=("PASS", "FAIL", "NEEDS_HUMAN_INPUT"))
    p_verdict.add_argument("iteration", type=int)
    p_verdict.add_argument("tree_sha")
    p_verdict.add_argument("reason", nargs="*")

    p_snap = sub.add_parser("snapshot", help="write a redacted memory snapshot")
    p_snap.add_argument("--query", required=True)
    p_snap.add_argument("--out", required=True)
    p_snap.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    if args.command == "ingest":
        if not os.path.isdir(args.job_dir):
            print(f"job dir not found: {args.job_dir}")
            return 2
        return ingest(args.job_dir, args.data_dir, args.cwd)
    if args.command == "verdict":
        if not 1 <= args.iteration <= 99 or not re.fullmatch(r"[0-9a-f]{40,64}", args.tree_sha):
            print("iteration must be 1..99 and tree_sha a git sha")
            return 2
        return verdict(
            args.job_id, args.verdict, args.iteration, args.tree_sha, " ".join(args.reason)[:300],
            args.data_dir, args.cwd,
        )
    if not 1 <= args.limit <= 50:
        print("--limit must be between 1 and 50")
        return 2
    return snapshot(args.query, args.out, args.limit, args.data_dir)


if __name__ == "__main__":
    sys.exit(main())
