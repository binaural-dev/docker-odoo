#!/usr/bin/env python3
"""Seed the Engram memory with the lessons kept in Claude's auto-memory directory.

Seeds ``feedback_*`` (working rules), ``reference_*`` (environment gotchas) and ``project_*`` (ticket state), so
OpenCode and subagents can read what Claude already knows. Use ``--no-project`` to skip ``project_*``.

Idempotent: every memory gets a fixed ``topic_key``, so a second run updates the same observations instead of
duplicating them. Client names and secrets are redacted before anything is written (see sdd_memory_common).

Exit codes: 0 all memories saved (or dry-run done), 1 some saves failed, 2 Engram not available.
"""

import argparse
import glob
import hashlib
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdd_memory_capture import pending_judgment_ids  # noqa: E402
from sdd_memory_common import (  # noqa: E402
    DEFAULT_DATA_DIR,
    EngramMcp,
    EngramMcpError,
    ascii_keywords,
    find_engram_binary,
    parse_frontmatter,
    redact,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MEMORY_DIR = os.path.join(
    os.path.expanduser("~"), ".claude", "projects", "-home-binlp011-sources-docker-multi", "memory"
)
SESSION_PREFIX = "sdd-memory-seed"
# Reachable from other repos only with all_projects:true (mem_search) or `engram search --all`:
# the scope value does not change search visibility, so it stays "project" to keep existing upserts.
SCOPE = "project"

# prefix -> (topic_key namespace, engram type)
PREFIXES = {
    "feedback_": ("feedback", "learning"),
    "reference_": ("entorno", "config"),
}
PROJECT_PREFIX = ("project_", ("proyecto", "discovery"))


def clean_slug(raw):
    """Generic topic_key part from a memory filename: client, database and ticket words removed.

    A short hash of the original name is appended so two files never share a key, even when their generic
    words coincide (e.g. two tickets that both reduce to ``ticket``).
    """
    text, _ = redact(raw.replace("_", " "))
    text = re.sub(r"<([\w-]+)>", r"\1", text)
    text = re.sub(r"(?i)\bhu\s*\d+\b", "ticket", text)
    text = re.sub(r"(?i)\bhu\s+dev\b", "rol-bd", text)
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]
    return f"{base}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:6]}"


def build_items(memory_dir, include_project=True):
    prefixes = dict(PREFIXES)
    if include_project:
        prefixes[PROJECT_PREFIX[0]] = PROJECT_PREFIX[1]

    items = []
    for path in sorted(glob.glob(os.path.join(memory_dir, "*.md"))):
        filename = os.path.basename(path)
        if filename == "MEMORY.md":
            continue
        prefix = next((p for p in prefixes if filename.startswith(p)), None)
        if prefix is None:
            continue
        namespace, mem_type = prefixes[prefix]
        slug = clean_slug(filename[len(prefix) : -3])

        with open(path, encoding="utf-8") as handle:
            fields, body = parse_frontmatter(handle.read())
        name = fields.get("name", slug)
        description = fields.get("description", "")

        clean_name, n_name = redact(name)
        clean_description, n_description = redact(description)
        clean_body, n_body = redact(body.strip())

        counts = {}
        for part in (n_name, n_description, n_body):
            for label, value in part.items():
                counts[label] = counts.get(label, 0) + value

        content = f"{clean_description}\n\n{clean_body}\n\nkeywords: {ascii_keywords(clean_name, clean_description)}"
        items.append(
            {
                "file": filename,
                "topic_key": f"{namespace}/{slug}",
                "title": clean_name,
                "type": mem_type,
                "content": content.strip(),
                "redactions": counts,
            }
        )
    return items


def describe(items):
    for item in items:
        redactions = ", ".join(f"{k}={v}" for k, v in sorted(item["redactions"].items())) or "none"
        print(f"  {item['topic_key']:<42} type={item['type']:<9} bytes={len(item['content']):<6} redactions: {redactions}")


def seed(items, binary, data_dir):
    # Ended sessions cannot be reopened, so every run gets its own session id.
    session_id = f"{SESSION_PREFIX}-{uuid.uuid4().hex[:12]}"
    client = EngramMcp(binary, cwd=REPO_ROOT, data_dir=data_dir)
    saved, failed = 0, 0
    try:
        try:
            client.call("mem_session_start", {"id": session_id, "directory": REPO_ROOT})
        except EngramMcpError as exc:
            print(f"warning: session start: {exc} (continuing; saves will report the real state)")
        for item in items:
            try:
                text = client.call(
                    "mem_save",
                    {
                        "title": item["title"],
                        "type": item["type"],
                        "topic_key": item["topic_key"],
                        "content": item["content"],
                        "session_id": session_id,
                        "scope": SCOPE,
                        "capture_prompt": False,
                    },
                )
                saved += 1
            except EngramMcpError as exc:
                failed += 1
                print(f"FAILED {item['topic_key']}: {exc}")
                continue
            # Similar seed lessons are related, not contradictory: judge them so a re-run leaves no pending relations.
            for judgment_id in pending_judgment_ids(text):
                try:
                    client.call(
                        "mem_judge",
                        {
                            "judgment_id": judgment_id,
                            "relation": "related",
                            "reason": "Siembra de auto-memoria: lecciones afines entre sí, sin contradicción.",
                            "session_id": session_id,
                        },
                    )
                except EngramMcpError as exc:
                    print(f"warning: judge {judgment_id}: {exc}")
        try:
            client.call("mem_session_end", {"id": session_id})
        except EngramMcpError as exc:
            print(f"warning: session end: {exc}")
    finally:
        client.close()
    return saved, failed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory-dir", default=DEFAULT_MEMORY_DIR, help="Claude auto-memory directory")
    parser.add_argument("--data-dir", default=None, help=f"ENGRAM_DATA_DIR (default: env or {DEFAULT_DATA_DIR})")
    parser.add_argument("--no-project", action="store_true", help="skip project_* files (ticket state)")
    parser.add_argument("--dry-run", action="store_true", help="show what would be saved, write nothing")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.memory_dir):
        print(f"memory dir not found: {args.memory_dir}")
        return 2

    items = build_items(args.memory_dir, include_project=not args.no_project)
    print(f"{len(items)} memories from {args.memory_dir}")
    describe(items)
    if args.dry_run:
        print("dry-run: nothing written")
        return 0

    binary = find_engram_binary()
    if not os.path.exists(binary):
        print(f"engram binary not found: {binary} (set ENGRAM_BIN)")
        return 2
    try:
        saved, failed = seed(items, binary, args.data_dir)
    except (EngramMcpError, OSError) as exc:
        print(f"cannot run engram mcp: {exc}")
        return 2
    print(f"saved={saved} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
