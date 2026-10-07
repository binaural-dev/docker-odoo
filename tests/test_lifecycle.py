"""Tests for `odoo_cli.core.actions.lifecycle` — currently just the
production-safety hard-block on `remove_odoo` (no other lifecycle action
had test coverage before this).

Run with::

    python3 -m unittest tests.test_lifecycle -v
"""

from __future__ import annotations

import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.actions.lifecycle import remove_odoo  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
