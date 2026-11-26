"""Tests for the database picker shared by update/shell/psql/pw.

Run with::

    python3 -m unittest tests.test_database_prompt -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core import instance as instance_mod  # noqa: E402
from odoo_cli.core.actions.modules import update  # noqa: E402
from odoo_cli.core.prompts import prompt_for_database  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402

LISTING = "odoo_cli.core.prompts.list_instance_databases_with_error"


def _lone_config():
    """'acme' alone on 'v17', without db_filter (like a client's server)."""
    return _sample_config()


def _shared_config():
    config = _sample_config()
    config["instances"]["beta"] = dict(config["instances"]["acme"], external_port=8070)
    return config


def _warnings(runner):
    return [text for level, text in runner.messages if level == "warn"]


class PromptForDatabaseTest(unittest.TestCase):
    def test_lone_instance_without_filter_gives_no_warning(self):
        runner = FakeRunner()
        with patch(LISTING, return_value=(["acme", "acme_test"], "")), \
                patch("odoo_cli.core.prompts.prompt_selection", return_value="acme"):
            prompt_for_database(runner, _lone_config(), "acme")
        self.assertEqual(_warnings(runner), [])

    def test_shared_service_without_filter_warns(self):
        runner = FakeRunner()
        with patch(LISTING, return_value=(["acme", "beta"], "")), \
                patch("odoo_cli.core.prompts.prompt_selection", return_value="acme"):
            prompt_for_database(runner, _shared_config(), "acme")
        self.assertEqual(len(_warnings(runner)), 1)
        self.assertIn("--db-filter", _warnings(runner)[0])

    def test_single_database_is_picked_and_named(self):
        runner = FakeRunner()
        with patch(LISTING, return_value=(["acme"], "")), \
                patch("odoo_cli.core.prompts.prompt_selection") as menu:
            self.assertEqual(prompt_for_database(runner, _lone_config(), "acme"), "acme")
        menu.assert_not_called()
        self.assertIn("Base de datos: acme", runner.messages[-1][1])

    def test_single_database_not_auto_picked_when_disabled(self):
        with patch(LISTING, return_value=(["acme"], "")), \
                patch("odoo_cli.core.prompts.prompt_selection", return_value="acme") as menu:
            prompt_for_database(FakeRunner(), _lone_config(), "acme", auto_single=False)
        menu.assert_called_once()

    def test_several_databases_show_menu_with_all(self):
        with patch(LISTING, return_value=(["a", "b"], "")), \
                patch("odoo_cli.core.prompts.prompt_selection", return_value="all") as menu:
            result = prompt_for_database(
                FakeRunner(), _lone_config(), "acme", allow_all=True
            )
        self.assertEqual(result, "all")
        values = [value for _, value in menu.call_args.args[1]]
        self.assertEqual(values, ["all", "a", "b"])

    def test_listing_failure_shows_reason_then_asks(self):
        runner = FakeRunner(text_answers=["acme"])
        reason = 'service "db-v17" is not running'
        with patch(LISTING, return_value=(None, reason)):
            result = prompt_for_database(runner, _lone_config(), "acme")
        self.assertEqual(result, "acme")
        self.assertIn(reason, _warnings(runner)[0])
        self.assertIn("./odoo start acme", _warnings(runner)[0])


class ListingErrorReasonTest(unittest.TestCase):
    def test_reason_is_the_last_stderr_line(self):
        failed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="",
            stderr='\nservice "db-v17" is not running\n',
        )
        with patch("odoo_cli.core.instance.subprocess.run", return_value=failed):
            databases, error = instance_mod.list_instance_databases_with_error(
                _lone_config(), "acme"
            )
        self.assertIsNone(databases)
        self.assertEqual(error, 'service "db-v17" is not running')


class UpdateAllTest(unittest.TestCase):
    def test_all_reports_the_reason_when_listing_fails(self):
        runner = FakeRunner()
        with patch(
            "odoo_cli.core.instance.list_instance_databases_with_error",
            return_value=(None, "connection refused"),
        ), self.assertRaises(SystemExit):
            update(runner, _lone_config(), "acme", "all")
        self.assertIn("connection refused", runner.messages[-1][1])

    def test_all_updates_every_database(self):
        with patch(
            "odoo_cli.core.instance.list_instance_databases_with_error",
            return_value=(["a", "b"], ""),
        ), patch(
            "odoo_cli.core.actions.modules.bash_update_modules", return_value=0
        ) as run:
            update(FakeRunner(), _lone_config(), "acme", "all")
        self.assertEqual([c.args[3] for c in run.call_args_list], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
