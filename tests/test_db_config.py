"""Tests for the new ``./odoo config --db-filter`` and ``./odoo db-config`` features.

Run with::

    python3 -m unittest tests.test_db_config -v
"""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.actions.instance_config import (  # noqa: E402
    _SENTINEL,
    _DB_CONFIGS,
    configure_db,
    configure_instance,
)
from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _config():
    cfg = _sample_config()
    cfg["odoo_configs"]["base"].update({"list_db": True, "workers": 4})
    cfg["odoo_configs"]["grande"] = {"admin_password": "admin", "workers": 80}
    # Give the DB service a 'config' field
    cfg["databases"]["v17"]["config"] = "postgresql.small.conf"
    return cfg


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_db_config_")
        self.regenerated = []
        patcher = patch(
            "odoo_cli.core.actions.instance_state._regenerate_configs",
            side_effect=self.regenerated.append,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, config):
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(config, f)

    def _read_instance(self, instance="acme"):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)["instances"][instance]

    def _read_database(self, db="v17"):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)["databases"][db]


# ===========================================================================
# configure_instance  –  db_filter argument tests
# ===========================================================================

class ConfigureInstanceDbFilterTest(_Base):
    """Tests for the new db_filter parameter of configure_instance."""

    def _run(self, db_filter=_SENTINEL, runner=None, config=None):
        cfg = config or _config()
        self._write(cfg)
        r = runner or FakeRunner()
        configure_instance(r, self.tmpdir, "acme", mode="prod", profile="base",
                           db_filter=db_filter)
        return r

    # --- sentinel (not passed) ---

    def test_sentinel_does_not_touch_existing_filter(self):
        cfg = _config()
        cfg["instances"]["acme"].setdefault("overwrite_odoo_config", {})["db_filter"] = "^old$"
        self._run(db_filter=_SENTINEL, config=cfg)
        saved = self._read_instance()
        self.assertEqual(saved["overwrite_odoo_config"]["db_filter"], "^old$")

    def test_sentinel_does_not_add_filter_when_absent(self):
        self._run(db_filter=_SENTINEL)
        saved = self._read_instance()
        self.assertNotIn("db_filter", saved.get("overwrite_odoo_config", {}))

    # --- explicit string ---

    def test_explicit_filter_is_set(self):
        self._run(db_filter="^release-acme$")
        saved = self._read_instance()
        self.assertEqual(saved["overwrite_odoo_config"]["db_filter"], "^release-acme$")
        self.assertEqual(len(self.regenerated), 1)

    def test_empty_string_removes_filter(self):
        cfg = _config()
        cfg["instances"]["acme"].setdefault("overwrite_odoo_config", {})["db_filter"] = "^old$"
        self._run(db_filter="", config=cfg)
        saved = self._read_instance()
        self.assertNotIn("db_filter", saved.get("overwrite_odoo_config", {}))

    # --- None (interactive prompt) ---

    def test_none_asks_interactively_and_sets(self):
        # FakeRunner.prompt_text returns the first text answer
        r = FakeRunner(text_answers=["^staging-acme$"])
        self._run(db_filter=None, runner=r)
        saved = self._read_instance()
        self.assertEqual(saved["overwrite_odoo_config"]["db_filter"], "^staging-acme$")

    def test_none_blank_prompt_keeps_existing(self):
        cfg = _config()
        cfg["instances"]["acme"].setdefault("overwrite_odoo_config", {})["db_filter"] = "^keep$"
        # prompt returns "" → keep existing
        r = FakeRunner(text_answers=[""])
        self._run(db_filter=None, runner=r, config=cfg)
        saved = self._read_instance()
        self.assertEqual(saved["overwrite_odoo_config"]["db_filter"], "^keep$")

    # --- no-op detection ---

    def test_no_changes_reported_when_filter_already_set_same(self):
        cfg = _config()
        cfg["instances"]["acme"]["production"] = True
        cfg["instances"]["acme"].setdefault("overwrite_odoo_config", {}).update(
            {"list_db": False, "db_filter": "^same$"}
        )
        r = self._run(db_filter="^same$", config=cfg)
        all_text = " ".join(t for _, t in r.messages)
        self.assertIn("Sin cambios", all_text)
        self.assertEqual(self.regenerated, [])


# ===========================================================================
# configure_db  –  db-config command tests
# ===========================================================================

class ConfigureDbTest(_Base):

    def _run(self, db_service=None, db_config=None, runner=None, config=None):
        cfg = config or _config()
        self._write(cfg)
        r = runner or FakeRunner()
        configure_db(r, self.tmpdir, db_service=db_service, db_config=db_config)
        return r

    def test_sets_config_explicitly(self):
        self._run(db_service="v17", db_config="postgresql.large.conf")
        saved = self._read_database()
        self.assertEqual(saved["config"], "postgresql.large.conf")
        self.assertEqual(len(self.regenerated), 1)

    def test_no_change_when_already_set(self):
        r = self._run(db_service="v17", db_config="postgresql.small.conf")
        all_text = " ".join(t for _, t in r.messages)
        self.assertIn("Sin cambios", all_text)
        self.assertEqual(self.regenerated, [])

    def test_invalid_config_name_exits(self):
        with self.assertRaises(SystemExit):
            self._run(db_service="v17", db_config="postgresql.huge.conf")

    def test_unknown_db_service_exits(self):
        with self.assertRaises(SystemExit):
            self._run(db_service="no-existe", db_config="postgresql.large.conf")

    def test_auto_selects_single_service(self):
        # Only v17 in the sample config → auto-selects without prompt
        r = self._run(db_service=None, db_config="postgresql.xlarge.conf")
        saved = self._read_database()
        self.assertEqual(saved["config"], "postgresql.xlarge.conf")
        all_text = " ".join(t for _, t in r.messages)
        # Should mention auto-selection
        self.assertIn("v17", all_text)

    def test_asks_service_when_multiple(self):
        cfg = _config()
        cfg["databases"]["v19"] = dict(cfg["databases"]["v17"], port=6001,
                                       config="postgresql.medium.conf")
        self._write(cfg)
        # FakeRunner.select_one returns first from select_one_answers → v19
        r = FakeRunner(select_one_answers=["v19"])
        configure_db(r, self.tmpdir, db_service=None,
                     db_config="postgresql.large.conf")
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            saved = json.load(f)["databases"]["v19"]
        self.assertEqual(saved["config"], "postgresql.large.conf")

    def test_asks_config_interactively(self):
        # FakeRunner.select_one returns first from select_one_answers
        r = FakeRunner(select_one_answers=["postgresql.xlarge.conf"])
        self._run(db_service="v17", db_config=None, runner=r)
        saved = self._read_database()
        self.assertEqual(saved["config"], "postgresql.xlarge.conf")

    def test_all_valid_configs_accepted(self):
        for conf in _DB_CONFIGS:
            cfg = _config()
            self._write(cfg)
            self.regenerated.clear()
            configure_db(FakeRunner(), self.tmpdir, db_service="v17", db_config=conf)
            if conf != "postgresql.small.conf":  # small.conf is the initial value
                self.assertEqual(len(self.regenerated), 1)
            # restore
            cfg["databases"]["v17"]["config"] = "postgresql.small.conf"


# ===========================================================================
# Launcher integration  –  argparse wiring for db-config
# ===========================================================================

class LauncherDbConfigTest(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader(
            "odoo_launcher", os.path.join(REPO_ROOT, "odoo")
        )
        spec = importlib.util.spec_from_loader("odoo_launcher", loader)
        self.launcher = importlib.util.module_from_spec(spec)
        loader.exec_module(self.launcher)
        self.tmpdir = tempfile.mkdtemp(prefix="test_db_config_launcher_")
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(_config(), f)
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _main(self, *argv):
        with patch.object(self.launcher, "BASE_PATH", self.tmpdir), \
                patch.object(sys, "argv", ["odoo", *argv]), \
                patch("odoo_cli.core.dispatch.configure_db") as action:
            self.launcher.main()
        return action

    def test_db_config_positionals_reach_action(self):
        action = self._main("db-config", "v17", "postgresql.xlarge.conf")
        self.assertEqual(action.call_args.kwargs.get("db_service"), "v17")
        self.assertEqual(action.call_args.kwargs.get("db_config"), "postgresql.xlarge.conf")

    def test_db_config_no_args_uses_none(self):
        action = self._main("db-config")
        self.assertIsNone(action.call_args.kwargs.get("db_service"))
        self.assertIsNone(action.call_args.kwargs.get("db_config"))

    def test_db_config_invalid_choice_argparse_error(self):
        with self.assertRaises(SystemExit), patch("sys.stderr"):
            self._main("db-config", "v17", "postgresql.huge.conf")


class LauncherConfigDbFilterTest(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader(
            "odoo_launcher", os.path.join(REPO_ROOT, "odoo")
        )
        spec = importlib.util.spec_from_loader("odoo_launcher", loader)
        self.launcher = importlib.util.module_from_spec(spec)
        loader.exec_module(self.launcher)
        self.tmpdir = tempfile.mkdtemp(prefix="test_config_dbfilter_")
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(_config(), f)
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _main(self, *argv):
        with patch.object(self.launcher, "BASE_PATH", self.tmpdir), \
                patch.object(sys, "argv", ["odoo", *argv]), \
                patch("odoo_cli.core.dispatch.configure_instance") as action:
            self.launcher.main()
        return action

    def test_db_filter_value_reaches_action(self):
        action = self._main("config", "acme", "prod", "base", "--db-filter", "^my-db$")
        self.assertEqual(action.call_args.kwargs.get("db_filter"), "^my-db$")

    def test_db_filter_flag_alone_passes_none(self):
        action = self._main("config", "acme", "prod", "base", "--db-filter")
        self.assertIsNone(action.call_args.kwargs.get("db_filter"))

    def test_no_db_filter_passes_sentinel(self):
        from odoo_cli.core.actions.instance_config import _SENTINEL
        action = self._main("config", "acme", "prod", "base")
        self.assertIs(action.call_args.kwargs.get("db_filter"), _SENTINEL)


if __name__ == "__main__":
    unittest.main()
