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
from odoo_cli.core.actions.instance_config import KEEP, configure_instance  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _config():
    config = _sample_config()
    config["odoo_configs"]["base"].update({"list_db": True, "workers": 4})
    config["odoo_configs"]["grande"] = {"admin_password": "admin", "workers": 80}
    config["databases"]["v18"] = dict(config["databases"]["v17"], port=6001)
    config["instances"]["beta"] = {
        "odoo_version": "17.0",
        "external_port": 8070,
        "database": "v18",
        "odoo_config": "base",
        "enabled": False,
    }
    return config


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

    def _read(self, instance="acme"):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)["instances"][instance]

    def _configure(self, mode=None, profile=None, config=None, instance="acme",
                   runner=None):
        self._write(config or _config())
        runner = runner or FakeRunner()
        configure_instance(runner, self.tmpdir, instance, mode=mode, profile=profile)
        return runner

    def test_prod_preset(self):
        self._configure("prod", "base")
        saved = self._read()
        self.assertIs(saved["production"], True)
        self.assertIs(saved["overwrite_odoo_config"]["list_db"], False)
        self.assertEqual(len(self.regenerated), 1)

    def test_spanish_alias(self):
        self._configure("produccion", "base")
        self.assertIs(self._read()["production"], True)

    def test_profile_is_switched_without_touching_profiles(self):
        self._configure("test", "grande")
        self.assertEqual(self._read()["odoo_config"], "grande")
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            self.assertEqual(json.load(f)["odoo_configs"]["base"]["workers"], 4)

    def test_asks_mode_and_profile_when_missing(self):
        runner = FakeRunner(select_one_answers=["prod", "grande"])
        self._configure(runner=runner)
        saved = self._read()
        self.assertIs(saved["production"], True)
        self.assertEqual(saved["odoo_config"], "grande")

    def test_single_profile_is_not_asked(self):
        config = _config()
        del config["odoo_configs"]["grande"]
        runner = FakeRunner(select_one_answers=["prod"])
        self._configure(config=config, runner=runner)
        self.assertEqual(self._read()["odoo_config"], "base")

    def test_cancelling_the_menu_writes_nothing(self):
        runner = FakeRunner(select_one_answers=[None])
        self._configure(runner=runner)
        self.assertNotIn("production", self._read())
        self.assertEqual(self.regenerated, [])

    def test_prod_to_test_asks_and_can_be_declined(self):
        config = _config()
        config["instances"]["acme"]["production"] = True
        self._configure("test", "base", config=config,
                        runner=FakeRunner(confirm_answers=[False]))
        self.assertIs(self._read()["production"], True)
        self.assertEqual(self.regenerated, [])

    def test_prod_to_test_when_confirmed(self):
        config = _config()
        config["instances"]["acme"]["production"] = True
        self._configure("test", "base", config=config,
                        runner=FakeRunner(confirm_answers=[True]))
        saved = self._read()
        self.assertIs(saved["production"], False)
        self.assertIs(saved["overwrite_odoo_config"]["list_db"], True)

    def test_no_changes(self):
        config = _config()
        config["instances"]["acme"]["production"] = True
        config["instances"]["acme"]["overwrite_odoo_config"] = {"list_db": False}
        runner = self._configure("prod", "base", config=config)
        self.assertIn("Sin cambios", runner.messages[-1][1])
        self.assertEqual(self.regenerated, [])

    def test_invalid_result_writes_nothing(self):
        config = _config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {"dev_mode": True}
        runner = FakeRunner()
        with self.assertRaises(SystemExit):
            self._configure("prod", "base", config=config, runner=runner)
        self.assertNotIn("production", self._read())
        self.assertIn("No se guardó nada", runner.messages[-1][1])

    def test_disabled_instance_can_be_configured(self):
        self._configure("prod", "base", instance="beta")
        self.assertIs(self._read("beta")["production"], True)

    def test_unknown_instance_or_profile(self):
        with self.assertRaises(SystemExit):
            self._configure("prod", "base", instance="no-existe")
        with self.assertRaises(SystemExit):
            self._configure("prod", "no-existe")

    def test_never_prints_secrets(self):
        config = _config()
        config["odoo_configs"]["base"]["admin_password"] = "m4ster-pw"
        runner = self._configure("prod", "base", config=config)
        output = "\n".join(text for _, text in runner.messages)
        self.assertNotIn("m4ster-pw", output)


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
    """Arguments must reach ``configure_instance`` from the real CLI."""

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

    def test_everything_given(self):
        action = self._main("config", "acme", "prod", "grande")
        self.assertEqual(action.call_args.args[2], "acme")
        kwargs = action.call_args.kwargs
        self.assertEqual(kwargs["mode"], "prod")
        self.assertEqual(kwargs["profile"], "grande")
        self.assertIs(kwargs["db_filter"], KEEP)

    def test_nothing_given_prompts(self):
        action = self._main("config")
        self.assertEqual(action.call_args.args[2], "elegida")
        kwargs = action.call_args.kwargs
        self.assertIsNone(kwargs["mode"])
        self.assertIsNone(kwargs["profile"])
        self.assertIs(kwargs["db_filter"], KEEP)

    def test_unknown_mode_is_an_argparse_error(self):
        with self.assertRaises(SystemExit), patch("sys.stderr"):
            self._main("config", "acme", "staging")


if __name__ == "__main__":
    unittest.main()
