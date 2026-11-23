"""Tests for ``odoo_cli.core.actions.testing.run_tests``: every flag that
``./odoo test`` accepts must reach the ``scripts/odoo-test`` subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from odoo_cli.core.actions import testing  # noqa: E402


def _args(**overrides) -> Namespace:
    values = dict(
        module="mod_a,mod_b", db=None, tags="all", recursive=False, exclude="",
        no_confirm=False, no_rm_db=False, dry_run=False, out_coverage_json=None,
        out_json=None, out_logs=None, out_verbose=False, per_module_db=False,
        out_summary_json=None, all_verbose=False,
    )
    values.update(overrides)
    return Namespace(**values)


class RunTestsForwardingTest(unittest.TestCase):

    def _run(self, args: Namespace, base_path: str = REPO_ROOT) -> list:
        with patch.object(testing, "_resolve_running_service", return_value="odoo-demo"), \
             patch.object(testing, "resolve_container_addon_paths", return_value=["/home/odoo/src/custom/demo"]), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaises(SystemExit):
                testing.run_tests(MagicMock(), {}, base_path, "demo", args)
        return run.call_args.args[0]

    def test_forwards_no_confirm(self):
        cmd = self._run(_args(recursive=True, no_confirm=True))
        self.assertIn("--recursive", cmd)
        self.assertIn("--no-confirm", cmd)

    def test_forwards_per_module_db_and_summary(self):
        cmd = self._run(_args(per_module_db=True, out_summary_json="/tmp/out"))
        self.assertIn("--per-module-db", cmd)
        self.assertEqual(cmd[cmd.index("--out-summary-json") + 1], "/tmp/out")

    def test_omits_flags_not_given(self):
        cmd = self._run(_args())
        for flag in ("--no-confirm", "--per-module-db", "--out-summary-json"):
            self.assertNotIn(flag, cmd)

    def test_all_verbose_sets_summary_only_with_per_module_db(self):
        with tempfile.TemporaryDirectory() as base:
            logs = os.path.join(base, "logs")
            cmd = self._run(_args(all_verbose=True, per_module_db=True), base_path=base)
            self.assertEqual(cmd[cmd.index("--out-summary-json") + 1], logs)
            cmd = self._run(_args(all_verbose=True), base_path=base)
            self.assertNotIn("--out-summary-json", cmd)


if __name__ == "__main__":
    unittest.main()
