"""Tests for ``./odoo config`` and the production nginx hardening.

Run with::

    python3 -m unittest tests.test_instance_config -v
"""

from __future__ import annotations

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

from generators.nginx_generator import generate_nginx_config  # noqa: E402
from odoo_cli.core.actions import instance_config  # noqa: E402
from odoo_cli.core.actions.instance_config import (  # noqa: E402
    configure_instance,
    parse_size,
)

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _config():
    config = _sample_config()
    config["odoo_configs"]["base"].update({"list_db": True, "workers": 4})
    config["databases"]["v18"] = dict(config["databases"]["v17"], port=6001)
    config["instances"]["beta"] = {
        "odoo_version": "17.0",
        "external_port": 8070,
        "database": "v18",
        "odoo_config": "base",
        "enabled": False,
    }
    return config


class ParseSizeTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_size("2G"), 2 * 1024 ** 3)
        self.assertEqual(parse_size("512m"), 512 * 1024 ** 2)
        self.assertEqual(parse_size("1.5G"), int(1.5 * 1024 ** 3))
        self.assertEqual(parse_size("2147483648"), 2147483648)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_size("dos gigas")


class ConfigureInstanceTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_instance_config_")
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

    def _read(self):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)

    def _configure(self, changes, config=None, instance="acme", runner=None):
        self._write(config or _config())
        runner = runner or FakeRunner()
        configure_instance(runner, self.tmpdir, instance, changes)
        return runner

    def test_production_turns_list_db_off(self):
        self._configure({"production": True})
        saved = self._read()["instances"]["acme"]
        self.assertIs(saved["production"], True)
        self.assertIs(saved["overwrite_odoo_config"]["list_db"], False)
        self.assertEqual(len(self.regenerated), 1)

    def test_changes_stay_in_the_instance(self):
        self._configure({"workers": 80, "limit_memory_soft": parse_size("2G")})
        saved = self._read()
        overwrite = saved["instances"]["acme"]["overwrite_odoo_config"]
        self.assertEqual(overwrite["workers"], 80)
        self.assertEqual(overwrite["limit_memory_soft"], 2 * 1024 ** 3)
        # The shared odoo_config is never touched.
        self.assertEqual(saved["odoo_configs"]["base"]["workers"], 4)

    def test_production_with_list_db_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._configure({"production": True, "list_db": True})
        self.assertNotIn("production", self._read()["instances"]["acme"])

    def test_invalid_result_writes_nothing(self):
        config = _config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {"dev_mode": True}
        runner = FakeRunner()
        with self.assertRaises(SystemExit):
            self._configure({"production": True}, config=config, runner=runner)
        self.assertNotIn("production", self._read()["instances"]["acme"])
        self.assertIn("No se guardó nada", runner.messages[-1][1])
        self.assertEqual(self.regenerated, [])

    def test_disabled_instance_can_be_configured(self):
        self._configure({"production": True}, instance="beta")
        self.assertIs(self._read()["instances"]["beta"]["production"], True)

    def test_back_to_test_instance(self):
        config = _config()
        config["instances"]["acme"]["production"] = True
        self._configure({"production": False}, config=config)
        self.assertIs(self._read()["instances"]["acme"]["production"], False)

    def test_unknown_instance(self):
        with self.assertRaises(SystemExit):
            self._configure({"workers": 2}, instance="no-existe")

    def test_without_changes_only_shows_and_hides_secrets(self):
        config = _config()
        config["instances"]["acme"]["db_user"] = "app_acme"
        config["instances"]["acme"]["db_password"] = "s3cr3t-db"
        config["odoo_configs"]["base"]["admin_password"] = "m4ster-pw"
        runner = self._configure({}, config=config)
        output = "\n".join(text for _, text in runner.messages)
        self.assertNotIn("m4ster-pw", output)
        self.assertNotIn("s3cr3t-db", output)
        self.assertIn("(definida)", output)
        self.assertEqual(self.regenerated, [])
        self.assertNotIn("production", self._read()["instances"]["acme"])


class NginxProductionTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_nginx_prod_")
        os.makedirs(os.path.join(self.tmpdir, ".resources", "nginx_configs"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _generate(self, config):
        path = generate_nginx_config(self.tmpdir, config)
        with open(path) as f:
            return f.read()

    def test_production_blocks_database_manager(self):
        config = _config()
        config["instances"]["acme"]["production"] = True
        self.assertIn("location ^~ /web/database/", self._generate(config))

    def test_non_production_keeps_database_manager(self):
        self.assertNotIn("/web/database/", self._generate(_config()))


class LauncherConfigTest(unittest.TestCase):
    """Flags must reach ``configure_instance`` from the real CLI."""

    def setUp(self):
        loader = importlib.machinery.SourceFileLoader(
            "odoo_launcher", os.path.join(REPO_ROOT, "odoo")
        )
        spec = importlib.util.spec_from_loader("odoo_launcher", loader)
        self.launcher = importlib.util.module_from_spec(spec)
        loader.exec_module(self.launcher)
        self.tmpdir = tempfile.mkdtemp(prefix="test_config_launcher_")
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(_config(), f)
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _main(self, *argv):
        with patch.object(self.launcher, "BASE_PATH", self.tmpdir), \
                patch.object(sys, "argv", ["odoo", *argv]), \
                patch("odoo_cli.core.dispatch.prompt_for_instance",
                      return_value="elegida"), \
                patch("odoo_cli.core.dispatch.configure_instance") as action:
            self.launcher.main()
        return action

    def test_only_given_flags_become_changes(self):
        action = self._main(
            "config", "acme", "--production", "--workers", "80",
            "--limit-memory-soft", "2G",
        )
        self.assertEqual(action.call_args.args[2], "acme")
        self.assertEqual(action.call_args.args[3], {
            "production": True,
            "workers": 80,
            "limit_memory_soft": 2 * 1024 ** 3,
        })

    def test_negative_flags(self):
        action = self._main("config", "acme", "--no-production", "--no-list-db")
        self.assertEqual(action.call_args.args[3], {
            "production": False, "list_db": False,
        })

    def test_no_flags_means_show(self):
        action = self._main("config", "acme")
        self.assertEqual(action.call_args.args[3], {})

    def test_without_instance_prompts(self):
        action = self._main("config")
        self.assertEqual(action.call_args.args[2], "elegida")

    def test_invalid_size_is_an_argparse_error(self):
        with self.assertRaises(SystemExit), \
                patch("sys.stderr"):
            self._main("config", "acme", "--limit-memory-soft", "mucho")


if __name__ == "__main__":
    unittest.main()
