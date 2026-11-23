"""Tests for ``./odoo provision-role`` target resolution and credentials.

Covers what runs BEFORE touching Postgres: every blocking problem is
reported at once, missing ``db_user``/``db_password`` can be generated
and persisted, and user-controlled values are quoted in the SQL.

Run with::

    python3 -m unittest tests.test_provision_role -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from generators.config_loader import load_config  # noqa: E402
from odoo_cli.core.actions import postgres  # noqa: E402
from odoo_cli.core.actions.postgres import (  # noqa: E402
    _ensure_credentials,
    _provision_problems,
    _resolve_provision_target,
    _sql_literal,
    _suggest_db_user,
    provision_role_sql,
)

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402

INSTANCE = "bufalinda-release"


def _config(db_filter="^bufalinda_release", **instance_fields):
    config = _sample_config()
    config["databases"]["v18"] = {
        "postgres_version": 16,
        "port": 6001,
        "user": "odoo",
        "password": "odoo",
    }
    config["instances"] = {
        INSTANCE: {
            "odoo_version": "17.0",
            "external_port": 8069,
            "database": "v17",
            "odoo_config": "base",
            **instance_fields,
        },
        "otra": {
            "odoo_version": "18.0",
            "external_port": 8070,
            "database": "v18",
            "odoo_config": "base",
            "enabled": False,
        },
    }
    if db_filter is not None:
        config["instances"][INSTANCE]["overwrite_odoo_config"] = {
            "db_filter": db_filter,
        }
    return config


class HelpersTest(unittest.TestCase):
    def test_suggest_db_user_follows_example_convention(self):
        self.assertEqual(_suggest_db_user(INSTANCE), "app_bufalinda_release")

    def test_suggest_db_user_is_a_valid_role_name(self):
        name = _suggest_db_user("Cliente.Con-Cosas" + "x" * 80)
        self.assertRegex(name, postgres._ROLE_NAME_RE)

    def test_sql_literal_doubles_quotes(self):
        self.assertEqual(_sql_literal("a'b"), "'a''b'")

    def test_generated_password_is_hex(self):
        self.assertRegex(postgres._generate_db_password(), r"^[0-9a-f]{48}$")


class ProvisionProblemsTest(unittest.TestCase):
    def test_complete_instance_has_no_problems(self):
        config = _config(db_user="app_x", db_password="secret")
        self.assertEqual(_provision_problems(config, INSTANCE), ([], False))

    def test_missing_credentials_flagged_apart(self):
        errors, missing = _provision_problems(_config(), INSTANCE)
        self.assertEqual(errors, [])
        self.assertTrue(missing)

    def test_invalid_role_name_is_an_error(self):
        config = _config(db_user="app-x; DROP", db_password="secret")
        errors, _ = _provision_problems(config, INSTANCE)
        self.assertEqual(len(errors), 1)
        self.assertIn("no es un nombre de rol valido", errors[0])

    def test_missing_db_filter_suggests_one(self):
        config = _config(db_filter=None, db_user="app_x", db_password="secret")
        errors, _ = _provision_problems(config, INSTANCE)
        self.assertEqual(len(errors), 1)
        self.assertIn('"^bufalinda_release"', errors[0])

    def test_dynamic_db_filter_is_rejected(self):
        config = _config(db_filter="^%d$", db_user="app_x", db_password="secret")
        errors, _ = _provision_problems(config, INSTANCE)
        self.assertEqual(len(errors), 1)


class ResolveProvisionTargetTest(unittest.TestCase):
    def test_reports_every_problem_at_once(self):
        runner = FakeRunner()
        with self.assertRaises(SystemExit):
            _resolve_provision_target(runner, _config(db_filter=None), INSTANCE)
        message = runner.messages[-1][1]
        self.assertIn("--generate-credentials", message)
        self.assertIn("db_filter", message)

    def test_resolves_complete_instance(self):
        config = _config(db_user="app_x", db_password="secret")
        target = _resolve_provision_target(FakeRunner(), config, INSTANCE)
        self.assertEqual(target["db_user"], "app_x")
        self.assertEqual(target["db_filter"], "^bufalinda_release")
        self.assertEqual(target["db_container"], "db-v17")


class EnsureCredentialsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_provision_role_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, config):
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(config, f)

    def _read(self):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)

    def _ensure(self, config, runner=None, generate=False):
        self._write(config)
        loaded = load_config(self.tmpdir)
        _ensure_credentials(runner or FakeRunner(), loaded, self.tmpdir, INSTANCE, generate)
        return loaded

    def test_generate_flag_persists_credentials(self):
        loaded = self._ensure(_config(), generate=True)
        saved = self._read()["instances"]
        self.assertEqual(saved[INSTANCE]["db_user"], "app_bufalinda_release")
        self.assertRegex(saved[INSTANCE]["db_password"], r"^[0-9a-f]{48}$")
        # Mirrored into the in-memory config the rest of the run uses.
        self.assertEqual(loaded["instances"][INSTANCE]["db_password"],
                         saved[INSTANCE]["db_password"])
        # Disabled instances are not dropped when rewriting the file.
        self.assertIn("otra", saved)

    def test_confirmation_yes_persists(self):
        self._ensure(_config(), runner=FakeRunner(confirm_answers=[True]))
        self.assertIn("db_user", self._read()["instances"][INSTANCE])

    def test_confirmation_no_aborts_without_writing(self):
        with self.assertRaises(SystemExit):
            self._ensure(_config(), runner=FakeRunner(confirm_answers=[False]))
        self.assertNotIn("db_user", self._read()["instances"][INSTANCE])

    def test_no_interactive_input_aborts_without_writing(self):
        runner = FakeRunner()
        with patch.object(runner, "confirm", side_effect=EOFError), \
                self.assertRaises(SystemExit):
            self._ensure(_config(), runner=runner)
        self.assertNotIn("db_user", self._read()["instances"][INSTANCE])

    def test_other_problems_abort_before_writing(self):
        runner = FakeRunner()
        with self.assertRaises(SystemExit):
            self._ensure(_config(db_filter=None), runner=runner, generate=True)
        self.assertNotIn("db_user", self._read()["instances"][INSTANCE])
        message = runner.messages[-1][1]
        self.assertIn("db_user", message)
        self.assertIn("db_filter", message)

    def test_keeps_existing_db_user_and_only_generates_password(self):
        self._ensure(_config(db_user="app_propio"), generate=True)
        saved = self._read()["instances"][INSTANCE]
        self.assertEqual(saved["db_user"], "app_propio")
        self.assertRegex(saved["db_password"], r"^[0-9a-f]{48}$")

    def test_suggested_role_taken_by_another_instance_aborts(self):
        config = _config()
        config["instances"]["otra"]["db_user"] = "app_bufalinda_release"
        config["instances"]["otra"]["db_password"] = "x"
        with self.assertRaises(SystemExit):
            self._ensure(config, generate=True)
        self.assertNotIn("db_user", self._read()["instances"][INSTANCE])

    def test_complete_instance_is_left_untouched(self):
        config = _config(db_user="app_x", db_password="secret")
        self._write(config)
        before = os.path.getmtime(os.path.join(self.tmpdir, "instances.json"))
        _ensure_credentials(FakeRunner(), load_config(self.tmpdir), self.tmpdir,
                            INSTANCE, False)
        after = os.path.getmtime(os.path.join(self.tmpdir, "instances.json"))
        self.assertEqual(before, after)


class ProvisionRoleSqlQuotingTest(unittest.TestCase):
    def test_password_and_db_filter_are_quoted(self):
        target = {
            "db_container": "db-v17",
            "bootstrap_user": "odoo",
            "bootstrap_password": "odoo",
            "db_user": "app_x",
            "db_password": "pa'ss",
            "db_filter": "^it's",
        }
        statements = []

        def fake_pg_exec(runner, container, user, password, dbname, sql, check=True):
            statements.append(sql)

        class _Listed:
            stdout = ""

        with patch.object(postgres, "_pg_exec", fake_pg_exec), \
                patch.object(postgres, "_container_id", lambda name: name), \
                patch.object(postgres.subprocess, "run", return_value=_Listed()) as run:
            provision_role_sql(FakeRunner(), target)

        self.assertTrue(any("PASSWORD 'pa''ss'" in sql for sql in statements))
        self.assertFalse(any(re.search(r"'pa'ss'", sql) for sql in statements))
        listing_sql = run.call_args.args[0][-1]
        self.assertIn("datname ~ '^it''s'", listing_sql)


class LauncherFlagTest(unittest.TestCase):
    """``--generate-credentials`` must reach the action from the real CLI."""

    def setUp(self):
        import importlib.machinery
        import importlib.util

        loader = importlib.machinery.SourceFileLoader(
            "odoo_launcher", os.path.join(REPO_ROOT, "odoo")
        )
        spec = importlib.util.spec_from_loader("odoo_launcher", loader)
        self.launcher = importlib.util.module_from_spec(spec)
        loader.exec_module(self.launcher)
        self.tmpdir = tempfile.mkdtemp(prefix="test_provision_launcher_")
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(_config(), f)
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _main(self, *argv):
        with patch.object(self.launcher, "BASE_PATH", self.tmpdir), \
                patch.object(sys, "argv", ["odoo", *argv]), \
                patch("odoo_cli.core.dispatch.provision_instance_role") as action:
            self.launcher.main()
        return action

    def test_flag_is_passed(self):
        action = self._main("provision-role", INSTANCE, "--generate-credentials")
        self.assertEqual(action.call_args.args[2], INSTANCE)
        self.assertEqual(action.call_args.args[3], self.tmpdir)
        self.assertTrue(action.call_args.kwargs["generate_credentials"])

    def test_flag_defaults_to_false(self):
        action = self._main("provision-role", INSTANCE)
        self.assertFalse(action.call_args.kwargs["generate_credentials"])


if __name__ == "__main__":
    unittest.main()
