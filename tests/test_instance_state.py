"""Tests for enable/disable and for the CLI with every instance disabled.

Regression: disabling every instance left ``load_config`` with an empty
``instances`` dict, ``_validate_config`` rejected it, and ``./odoo``
crashed before dispatching ANY action — including ``enable`` (the only
way out) and ``update-tags``/``update-tags-bulk``, which don't depend on
the ``enabled`` flag at all.

Run with::

    python3 -m unittest tests.test_instance_state -v
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

from generators.config_loader import (  # noqa: E402
    _validate_config,
    load_config,
    load_full_config,
)
from odoo_cli.core.actions import instance_state  # noqa: E402
from odoo_cli.core.actions.instance_state import set_instances_enabled  # noqa: E402
from odoo_cli.core.actions.validate import validate_instances  # noqa: E402

from tests.test_actions import FakeRunner  # noqa: E402
from tests.test_compose_generator import _sample_config  # noqa: E402


def _two_instance_config(acme_enabled=True, beta_enabled=True):
    """``acme`` and ``beta`` share DB ``v17``; ``gamma`` owns ``v18``."""
    config = _sample_config()
    config["databases"]["v18"] = {
        "postgres_version": 16,
        "port": 6001,
        "user": "odoo",
        "password": "odoo",
    }
    # Sharing a DB service requires a dedicated role + db_filter each
    # (see _validate_cron_dbfilter_isolation).
    config["instances"]["acme"].update({
        "enabled": acme_enabled,
        "db_user": "acme",
        "db_password": "acme",
        "overwrite_odoo_config": {"db_filter": "^acme"},
    })
    config["instances"]["beta"] = {
        "odoo_version": "17.0",
        "external_port": 8070,
        "database": "v17",
        "odoo_config": "base",
        "enabled": beta_enabled,
        "db_user": "beta",
        "db_password": "beta",
        "overwrite_odoo_config": {"db_filter": "^beta"},
    }
    config["instances"]["gamma"] = {
        "odoo_version": "18.0",
        "external_port": 8071,
        "database": "v18",
        "odoo_config": "base",
        "enabled": True,
    }
    return config


def _all_disabled_config():
    config = _two_instance_config(acme_enabled=False, beta_enabled=False)
    config["instances"]["gamma"]["enabled"] = False
    return config


class _TmpInstancesJsonMixin:
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_instance_state_")
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, config):
        with open(os.path.join(self.tmpdir, "instances.json"), "w") as f:
            json.dump(config, f)

    def _read(self):
        with open(os.path.join(self.tmpdir, "instances.json")) as f:
            return json.load(f)


class LoadConfigAllDisabledTest(_TmpInstancesJsonMixin, unittest.TestCase):
    def test_all_disabled_loads_with_no_instances(self):
        self._write(_all_disabled_config())
        config = load_config(self.tmpdir)
        self.assertEqual(config["instances"], {})

    def test_all_disabled_passes_validate_instances(self):
        self._write(_all_disabled_config())
        validate_instances(FakeRunner(), load_config(self.tmpdir))  # must not exit

    def test_full_config_keeps_disabled_instances(self):
        self._write(_all_disabled_config())
        config = load_full_config(self.tmpdir)
        self.assertEqual(set(config["instances"]), {"acme", "beta", "gamma"})

    def test_file_without_instances_is_still_rejected(self):
        config = _sample_config()
        config["instances"] = {}
        self._write(config)
        with self.assertRaises(ValueError):
            load_config(self.tmpdir)

    def test_validate_config_still_requires_instances_by_default(self):
        config = _sample_config()
        config["instances"] = {}
        with self.assertRaises(ValueError):
            _validate_config(config)
        _validate_config(config, require_instances=False)  # should not raise


def _load_launcher():
    """Import the extensionless ``./odoo`` launcher as a module."""
    path = os.path.join(REPO_ROOT, "odoo")
    loader = importlib.machinery.SourceFileLoader("odoo_launcher", path)
    spec = importlib.util.spec_from_loader("odoo_launcher", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class LauncherAllDisabledTest(_TmpInstancesJsonMixin, unittest.TestCase):
    """``./odoo`` must reach dispatch even when every instance is disabled."""

    @classmethod
    def setUpClass(cls):
        cls.launcher = _load_launcher()

    def setUp(self):
        super().setUp()
        self._write(_all_disabled_config())

    def _main(self, *argv):
        with patch.object(self.launcher, "BASE_PATH", self.tmpdir), \
                patch.object(sys, "argv", ["odoo", *argv]):
            return self.launcher.main()

    def test_update_tags_runs(self):
        with patch("odoo_cli.core.dispatch.update_tags") as update_tags:
            self._main("update-tags", "proj", "staging", "integra-addons", "17.0.1.0.0")
        update_tags.assert_called_once()
        self.assertEqual(update_tags.call_args.args[1], "proj")

    def test_update_tags_bulk_sees_disabled_projects(self):
        with patch("odoo_cli.core.dispatch.prompt_for_bulk_projects",
                   return_value=["proj"]) as prompt, \
                patch("odoo_cli.core.dispatch.update_tags_bulk") as bulk:
            self._main("update-tags-bulk", "17.0", "integra-addons", "17.0.1.0.0",
                       "--branch-origin", "staging")
        bulk.assert_called_once()
        # Prompted over the FULL config, so disabled instances are listed.
        full_config = prompt.call_args.args[1]
        self.assertEqual(set(full_config["instances"]), {"acme", "beta", "gamma"})

    def test_enable_runs(self):
        with patch("odoo_cli.core.dispatch.set_instances_enabled") as set_enabled:
            self._main("enable", "acme")
        set_enabled.assert_called_once()
        self.assertEqual(set_enabled.call_args.args[2], ["acme"])
        self.assertTrue(set_enabled.call_args.kwargs["enabled"])


class SetInstancesEnabledTest(_TmpInstancesJsonMixin, unittest.TestCase):
    """Disabling stops the containers before the compose file drops them."""

    def setUp(self):
        super().setUp()
        os.chdir(self.tmpdir)
        open(os.path.join(self.tmpdir, "docker-compose.generated.yml"), "w").close()
        self.events = []
        self.runner = FakeRunner()

    def _run(self, config, names, enabled, compose_services=None):
        self._write(config)
        if compose_services is None:
            compose_services = [
                "odoo-acme", "odoo-beta", "odoo-gamma", "db-v17", "db-v18", "nginx",
            ]

        def fake_subprocess_run(argv, **kwargs):
            self.events.append(("services",))
            return _Completed(0, "\n".join(compose_services) + "\n")

        def fake_docker_compose(runner, *args):
            self.events.append(("compose", *args))
            return 0

        def fake_regenerate(full_config):
            self.events.append(("regenerate",))

        with patch.object(instance_state.subprocess, "run", fake_subprocess_run), \
                patch("odoo_cli.core.actions.lifecycle._docker_compose",
                      fake_docker_compose), \
                patch.object(instance_state, "_regenerate_configs", fake_regenerate):
            set_instances_enabled(self.runner, self.tmpdir, names, enabled=enabled)

    def _stopped(self):
        stops = [e for e in self.events if e[:2] == ("compose", "stop")]
        return [service for e in stops for service in e[2:]]

    def test_disable_stops_before_regenerating(self):
        self._run(_two_instance_config(), ["gamma"], enabled=False)
        self.assertEqual(self._stopped(), ["odoo-gamma", "db-v18"])
        kinds = [e[0] for e in self.events]
        self.assertLess(kinds.index("compose"), kinds.index("regenerate"))
        self.assertFalse(self._read()["instances"]["gamma"]["enabled"])

    def test_shared_db_kept_while_another_instance_uses_it(self):
        self._run(_two_instance_config(), ["acme"], enabled=False)
        self.assertEqual(self._stopped(), ["odoo-acme"])

    def test_shared_db_stopped_when_every_user_is_disabled(self):
        self._run(_two_instance_config(), ["acme", "beta"], enabled=False)
        self.assertEqual(self._stopped(), ["odoo-acme", "odoo-beta", "db-v17"])

    def test_services_missing_from_compose_are_skipped(self):
        self._run(_two_instance_config(), ["acme", "gamma"], enabled=False,
                  compose_services=["odoo-gamma", "db-v18"])
        self.assertEqual(self._stopped(), ["odoo-gamma", "db-v18"])

    def test_disable_every_instance(self):
        self._run(_two_instance_config(), ["acme", "beta", "gamma"], enabled=False)
        saved = self._read()["instances"]
        self.assertFalse(any(inst["enabled"] for inst in saved.values()))
        # And the CLI can still load it afterwards.
        self.assertEqual(load_config(self.tmpdir)["instances"], {})

    def test_enable_from_all_disabled_never_stops_anything(self):
        self._run(_all_disabled_config(), ["acme"], enabled=True)
        self.assertEqual(self._stopped(), [])
        self.assertIn(("regenerate",), self.events)
        self.assertTrue(self._read()["instances"]["acme"]["enabled"])

    def test_already_disabled_is_a_no_op(self):
        self._run(_all_disabled_config(), ["acme"], enabled=False)
        self.assertEqual(self.events, [])


class _Completed:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


if __name__ == "__main__":
    unittest.main()
