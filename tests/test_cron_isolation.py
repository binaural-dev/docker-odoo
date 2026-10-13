"""Tests for the cron/db_filter isolation policy in config_loader and its
enforcement in the CLI dispatch.

The check used to live in ``_validate_config``, so one non-isolated
instance made every ``./odoo`` command fail. Now it only blocks the
commands that leave an Odoo with cron running (build/start/restart), scoped
to the requested instance; everything else just gets a warning.

Run with::

    python3 -m unittest tests.test_cron_isolation -v
"""

from __future__ import annotations

import argparse
import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from generators.config_loader import (  # noqa: E402
    _validate_config,
    cron_dbfilter_isolation_warning,
    enforce_cron_dbfilter_isolation,
)
from odoo_cli.core import dispatch as dispatch_mod  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _shared_config():
    """acme is isolated (own role + db_filter); beta shares v17 without it."""
    config = _sample_config()
    acme = config["instances"]["acme"]
    acme["db_user"] = "app_acme"
    acme["db_password"] = "x"
    acme["overwrite_odoo_config"] = {"db_filter": "^acme"}
    config["instances"]["beta"] = {
        "odoo_version": "17.0",
        "external_port": 8070,
        "database": "v17",
        "odoo_config": "base",
    }
    return config


class IsolationPolicyTest(unittest.TestCase):
    def test_validate_config_no_longer_enforces_isolation(self):
        _validate_config(_shared_config())  # must not raise

    def test_enforce_without_scope_checks_whole_group(self):
        with self.assertRaises(ValueError) as ctx:
            enforce_cron_dbfilter_isolation(_shared_config())
        self.assertIn("beta", str(ctx.exception))

    def test_enforce_scoped_to_isolated_instance_passes(self):
        enforce_cron_dbfilter_isolation(_shared_config(), ["acme"])

    def test_enforce_scoped_to_unisolated_instance_fails(self):
        with self.assertRaises(ValueError):
            enforce_cron_dbfilter_isolation(_shared_config(), ["beta"])

    def test_max_cron_threads_zero_is_an_escape_hatch(self):
        config = _shared_config()
        config["instances"]["beta"]["overwrite_odoo_config"] = {"max_cron_threads": 0}
        enforce_cron_dbfilter_isolation(config)
        self.assertIsNone(cron_dbfilter_isolation_warning(config))

    def test_duplicate_role_kept_when_scoped_to_either_side(self):
        config = _shared_config()
        beta = config["instances"]["beta"]
        beta["db_user"] = "app_acme"
        beta["db_password"] = "y"
        beta["overwrite_odoo_config"] = {"db_filter": "^beta"}
        for scope in (["acme"], ["beta"]):
            with self.assertRaises(ValueError):
                enforce_cron_dbfilter_isolation(config, scope)

    def test_warning_counts_affected_instances(self):
        warning = cron_dbfilter_isolation_warning(_shared_config())
        self.assertIn("1 de 2", warning)
        self.assertIn("'v17'", warning)

    def test_single_instance_service_needs_nothing(self):
        config = _sample_config()
        enforce_cron_dbfilter_isolation(config)
        self.assertIsNone(cron_dbfilter_isolation_warning(config))


class DispatchEnforcementTest(unittest.TestCase):
    def _dispatch(self, action, instance):
        runner = FakeRunner()
        args = argparse.Namespace(action=action, instance=instance, no_cache=False)
        with patch.object(dispatch_mod, "start_odoo") as start, \
                patch.object(dispatch_mod, "_resolve_instance", return_value=instance):
            rc = dispatch_mod.dispatch(runner, args, _shared_config(), ".")
        return rc, start, runner

    def test_start_unisolated_instance_is_blocked(self):
        rc, start, runner = self._dispatch("start", "beta")
        self.assertEqual(rc, 1)
        start.assert_not_called()
        self.assertTrue(any(level == "error" for level, _ in runner.messages))

    def test_start_isolated_instance_runs_despite_sibling(self):
        rc, start, _ = self._dispatch("start", "acme")
        start.assert_called_once()

    def test_start_all_is_blocked(self):
        rc, start, _ = self._dispatch("start", None)
        self.assertEqual(rc, 1)
        start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
