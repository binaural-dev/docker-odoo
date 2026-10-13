"""Tests for `odoo_cli.core.actions.lifecycle` — currently just the
production-safety hard-block on `remove_odoo` (no other lifecycle action
had test coverage before this).

Run with::

    python3 -m unittest tests.test_lifecycle -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.actions.lifecycle import remove_odoo  # noqa: E402
from odoo_cli.core.actions.access import list_containers  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _two_instance_config():
    config = _sample_config()
    config["instances"]["beta"] = dict(config["instances"]["acme"])
    config["instances"]["beta"]["external_port"] = 8070
    return config


class RemoveOdooProductionBlockTest(unittest.TestCase):
    def test_blocked_for_production_instance(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = True
        # Seed an answer that would only be consumed if confirm() were
        # actually reached — asserting it's still queued afterwards proves
        # the block happened before any prompt.
        runner = FakeRunner(confirm_answers=[True])

        with self.assertRaises(SystemExit) as ctx:
            remove_odoo(runner, config, "acme")
        self.assertEqual(ctx.exception.code, 1)

        self.assertEqual(runner._confirm_q, [True], "confirm() must never be called")
        self.assertTrue(
            any(level == "error" and "acme" in msg for level, msg in runner.messages),
            f"expected an error message naming the blocked instance, got {runner.messages}",
        )

    def test_allowed_for_non_production_instance(self):
        config = _sample_config()  # no "production" key at all
        runner = FakeRunner(confirm_answers=[False])  # decline, to avoid touching real docker

        remove_odoo(runner, config, "acme")

        self.assertEqual(runner._confirm_q, [], "confirm() should have been reached and consumed")
        self.assertFalse(
            any(level == "error" for level, _ in runner.messages),
            f"non-production instance must not be blocked, got {runner.messages}",
        )
        self.assertTrue(
            any("cancelada" in msg for _, msg in runner.messages),
            "declining the confirm should cancel the operation",
        )

    def test_allowed_for_explicitly_non_production_instance(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = False
        runner = FakeRunner(confirm_answers=[False])

        remove_odoo(runner, config, "acme")

        self.assertEqual(runner._confirm_q, [])
        self.assertFalse(any(level == "error" for level, _ in runner.messages))

    def test_remove_all_blocked_when_any_instance_is_production(self):
        config = _two_instance_config()
        config["instances"]["beta"]["production"] = True
        runner = FakeRunner(confirm_answers=[True])

        with self.assertRaises(SystemExit) as ctx:
            remove_odoo(runner, config, None)
        self.assertEqual(ctx.exception.code, 1)

        self.assertEqual(runner._confirm_q, [True], "confirm() must never be called")
        self.assertTrue(
            any(level == "error" and "beta" in msg for level, msg in runner.messages),
            f"expected an error message naming the production instance, got {runner.messages}",
        )

    def test_remove_all_allowed_when_no_instance_is_production(self):
        config = _two_instance_config()
        runner = FakeRunner(confirm_answers=[False])

        remove_odoo(runner, config, None)

        self.assertEqual(runner._confirm_q, [])
        self.assertFalse(any(level == "error" for level, _ in runner.messages))


class RemoveOdooPurgeTest(unittest.TestCase):
    """Second confirm of `remove <instance>`: repo + instances.json entry."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        config = _two_instance_config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {
            "addons": ["src/custom/acme"], "max_cron_threads": 0,
        }
        config["instances"]["beta"]["overwrite_odoo_config"] = {
            "addons": ["src/custom/beta"], "max_cron_threads": 0,
        }
        config["instances"]["gamma"] = json.loads(json.dumps(config["instances"]["acme"]))
        config["instances"]["gamma"]["external_port"] = 8071
        config["instances"]["gamma"]["enabled"] = False
        config["instances"]["gamma"]["overwrite_odoo_config"]["addons"] = ["src/custom/gamma"]
        self.raw = config
        self._write(config)
        for name in ("acme", "beta"):
            os.makedirs(os.path.join(self.base, "src", "custom", name, "mod"))

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, config):
        with open(os.path.join(self.base, "instances.json"), "w") as f:
            json.dump(config, f)

    def _read(self):
        with open(os.path.join(self.base, "instances.json")) as f:
            return json.load(f)

    def _remove(self, instance, confirms, config=None):
        runner = FakeRunner(confirm_answers=confirms)
        enabled = {
            n: c for n, c in (config or self.raw)["instances"].items()
            if c.get("enabled", True)
        }
        cli_config = dict(config or self.raw, instances=enabled)
        with patch("odoo_cli.core.actions.lifecycle.subprocess.run"), \
                patch("odoo_cli.core.actions.lifecycle.start_odoo") as start, \
                patch("odoo_cli.core.actions.instance_state._regenerate_configs") as regen:
            remove_odoo(runner, cli_config, instance, self.base)
        return runner, start, regen

    def test_purge_removes_repo_and_entry_and_keeps_disabled(self):
        runner, start, regen = self._remove("acme", [True, True])

        saved = self._read()["instances"]
        self.assertNotIn("acme", saved)
        self.assertIn("beta", saved)
        self.assertIn("gamma", saved, "disabled instances must survive the rewrite")
        self.assertFalse(os.path.exists(os.path.join(self.base, "src/custom/acme")))
        self.assertTrue(os.path.exists(os.path.join(self.base, "src/custom/beta")))
        regen.assert_called_once()
        start.assert_not_called()

    def test_declining_purge_keeps_repo_and_offers_restart(self):
        runner, start, regen = self._remove("acme", [True, False, True])

        self.assertIn("acme", self._read()["instances"])
        self.assertTrue(os.path.exists(os.path.join(self.base, "src/custom/acme")))
        regen.assert_not_called()
        start.assert_called_once()

    def test_repo_shared_with_other_instance_is_kept(self):
        self.raw["instances"]["beta"]["overwrite_odoo_config"]["addons"].append(
            "src/custom/acme/mod"
        )
        self._write(self.raw)

        runner, _, _ = self._remove("acme", [True, True])

        self.assertNotIn("acme", self._read()["instances"])
        self.assertTrue(os.path.exists(os.path.join(self.base, "src/custom/acme")))
        self.assertTrue(any("beta" in msg for _, msg in runner.messages))

    def test_purge_refused_when_no_enabled_instance_would_remain(self):
        self.raw["instances"]["beta"]["enabled"] = False
        self._write(self.raw)

        runner, _, regen = self._remove("acme", [True, True])

        self.assertIn("acme", self._read()["instances"])
        self.assertTrue(os.path.exists(os.path.join(self.base, "src/custom/acme")))
        regen.assert_not_called()
        self.assertTrue(any(level == "error" for level, _ in runner.messages))

    def test_remove_all_never_offers_purge(self):
        runner, start, regen = self._remove(None, [True, True])

        self.assertEqual(set(self._read()["instances"]), {"acme", "beta", "gamma"})
        regen.assert_not_called()
        start.assert_called_once()  # 2nd answer went to "levantar en blanco"


class ListContainersTest(unittest.TestCase):
    def _list(self, stdout, returncode=0):
        runner = FakeRunner()
        result = type("R", (), {"stdout": stdout, "stderr": "boom", "returncode": returncode})
        with patch("odoo_cli.core.actions.access.subprocess.run", return_value=result):
            list_containers(runner, _two_instance_config())
        return "\n".join(msg for _, msg in runner.messages)

    def test_table_from_ndjson(self):
        out = self._list(
            '{"Service": "odoo-acme", "Name": "multi-odoo-acme-1", "Status": "Up 2 hours"}\n'
            '{"Service": "nginx", "Name": "multi-nginx-1", "Status": "Up"}\n'
        )
        self.assertIn("acme", out)
        self.assertIn("multi-odoo-acme-1", out)
        self.assertIn("Up 2 hours", out)
        self.assertNotIn("beta", out)
        self.assertNotIn("nginx", out)

    def test_table_from_json_array(self):
        out = self._list('[{"Service": "odoo-beta", "Name": "c-beta", "State": "running"}]')
        self.assertIn("c-beta", out)
        self.assertIn("8070", out)

    def test_nothing_running(self):
        self.assertIn("No hay instancias", self._list(""))

    def test_compose_error_is_reported(self):
        self.assertIn("boom", self._list("", returncode=1))


if __name__ == "__main__":
    unittest.main()
