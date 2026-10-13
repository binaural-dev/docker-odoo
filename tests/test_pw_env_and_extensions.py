"""Regression tests for two issues found on a macOS + colima host:

* ``./odoo pw`` crashed with ``FileNotFoundError: 'docker'`` because the
  psql helpers replaced the environment with a fixed PATH (no
  /opt/homebrew/bin) and no HOME (so docker couldn't see its context).
* Odoo 19 failed with ``type "vector" does not exist`` on instances with a
  dedicated (NOSUPERUSER) role: pgvector is not a trusted extension, so
  ``provision-role`` now creates it as the bootstrap superuser.

Run with::

    python3 -m unittest tests.test_pw_env_and_extensions -v
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from generators import pw_helpers  # noqa: E402
from odoo_cli.core.actions import postgres  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CheckDbExistsEnvTest(unittest.TestCase):
    def test_inherits_host_environment(self):
        fake_env = {"PATH": "/opt/homebrew/bin:/usr/bin", "HOME": "/Users/x",
                    "DOCKER_CONTEXT": "colima"}
        seen = {}

        def fake_run(cmd, **kwargs):
            seen.update(kwargs["env"])
            return _Proc(0, "1\n")

        with patch.dict(os.environ, fake_env, clear=True), \
                patch.object(pw_helpers.subprocess, "run", side_effect=fake_run):
            self.assertEqual(
                pw_helpers._check_db_exists("odoo-a", "db", "u", 5432, "pw", "a", "c.yml"),
                (True, []),
            )
        self.assertEqual(seen["PATH"], fake_env["PATH"])
        self.assertEqual(seen["HOME"], "/Users/x")
        self.assertEqual(seen["DOCKER_CONTEXT"], "colima")
        self.assertEqual(seen["PGPASSWORD"], "pw")


class EnsureUntrustedExtensionsTest(unittest.TestCase):
    def _run(self, query_result):
        executed = []
        runner = FakeRunner()
        with patch.object(postgres, "_container_id", return_value="cid"), \
                patch.object(postgres.subprocess, "run", return_value=query_result), \
                patch.object(postgres, "_pg_exec",
                             side_effect=lambda *a, **k: executed.append((a[4], a[5]))):
            postgres._ensure_untrusted_extensions(runner, "db-v19", "boot", "pw", "acme")
        return executed, runner

    def test_creates_missing_available_extension(self):
        executed, _ = self._run(_Proc(0, "vector\n"))
        self.assertEqual(executed, [("acme", 'CREATE EXTENSION IF NOT EXISTS "vector";')])

    def test_nothing_to_do_when_installed_or_unavailable(self):
        executed, _ = self._run(_Proc(0, ""))
        self.assertEqual(executed, [])

    def test_query_failure_only_warns(self):
        executed, runner = self._run(_Proc(1, "", "boom"))
        self.assertEqual(executed, [])
        self.assertTrue(any(level == "warn" and "boom" in m for level, m in runner.messages))


if __name__ == "__main__":
    unittest.main()
