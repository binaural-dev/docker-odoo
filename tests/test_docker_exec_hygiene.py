"""Regression guard: every `docker exec`/`docker cp` in this repo must go
through `docker compose` (by *service* name), never a raw container name.

Why this matters: the real container name is namespaced by the Compose
project and is not guaranteed to equal the service name (``odoo-<instance>``,
``db-<db_name>``). A plain ``docker exec <name>``/``docker cp <name>:...``
silently breaks the moment that assumption stops holding — which is exactly
what happened when ``container_name:`` was removed from the generator to fix
the cross-deployment DB-sharing bug (2026-07-22). This test exists so that
regression can't creep back in unnoticed.

Run with::

    python3 -m unittest tests.test_docker_exec_hygiene -v
"""

from __future__ import annotations

import ast
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Only these roots are host-side orchestration code that shells out to
# `docker`. `.resources/entrypoint.d/` and friends run *inside* a container
# and never invoke docker themselves, so they're out of scope.
SCAN_ROOTS = ["odoo_cli", "scripts", os.path.join(".resources", "generators")]

BAD_SUBCOMMANDS = {"exec", "cp"}

# Raw `docker exec`/`docker cp` as adjacent words in shell text (bash
# scripts). "docker compose ... exec" never matches: "compose" sits between
# "docker" and "exec", so the two words aren't adjacent.
BASH_RAW_PATTERN = re.compile(r"\bdocker\s+(exec|cp)\b")


def _iter_source_files():
    for root_name in SCAN_ROOTS:
        root = os.path.join(REPO_ROOT, root_name)
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if os.path.isfile(path):
                    yield path


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def _is_python(path, text):
    if path.endswith(".py"):
        return True
    first_line = text.splitlines()[0] if text else ""
    return "python" in first_line


def _is_bash(path, text):
    if path.endswith(".py"):
        return False
    first_line = text.splitlines()[0] if text else ""
    return "bash" in first_line or "/sh" in first_line


def _bad_calls_in_python(text):
    """Flag any ``["docker", "exec", ...]``/``["docker", "cp", ...]`` list
    or tuple literal — i.e. "docker" and the risky subcommand are adjacent,
    with nothing (in particular no "compose") wedged between them.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    bad_lines = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        first_two = []
        for elt in node.elts[:2]:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                first_two.append(elt.value)
            else:
                break
        if len(first_two) == 2 and first_two[0] == "docker" and first_two[1] in BAD_SUBCOMMANDS:
            bad_lines.append(node.lineno)
    return bad_lines


def _bad_calls_in_bash(text):
    bad_lines = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if BASH_RAW_PATTERN.search(line):
            bad_lines.append(lineno)
    return bad_lines


class DockerExecHygieneTest(unittest.TestCase):
    def test_no_raw_docker_exec_or_cp(self):
        offenders = []
        for path in _iter_source_files():
            text = _read(path)
            if not text:
                continue

            rel = os.path.relpath(path, REPO_ROOT)
            if _is_python(path, text):
                bad_lines = _bad_calls_in_python(text)
            elif _is_bash(path, text):
                bad_lines = _bad_calls_in_bash(text)
            else:
                continue

            offenders.extend(f"{rel}:{lineno}" for lineno in bad_lines)

        self.assertFalse(
            offenders,
            "Raw `docker exec`/`docker cp` found (must go through `docker "
            "compose exec`/`docker compose cp` by service name instead, "
            "since the real container name is namespaced by the Compose "
            "project, not a bare `odoo-<instance>`/`db-<db_name>`):\n"
            + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
