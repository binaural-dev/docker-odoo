"""Tests for the `production`/`dev_mode` instance flags in config_loader.

`production` gates destructive CLI actions (see `remove_odoo` in
odoo_cli/core/actions/lifecycle.py); `dev_mode` toggles Odoo's `--dev=all`
in compose generation. The two must never coexist on the same instance.

Run with::

    python3 -m unittest tests.test_config_loader -v
"""

from __future__ import annotations

import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from generators.config_loader import (  # noqa: E402
    _validate_config,
    is_production_instance,
)

from tests.test_compose_generator import _sample_config  # noqa: E402


class IsProductionInstanceTest(unittest.TestCase):
    def test_defaults_to_false_when_missing(self):
        self.assertFalse(is_production_instance({}))

    def test_true_when_flagged(self):
        self.assertTrue(is_production_instance({"production": True}))

    def test_false_when_explicitly_false(self):
        self.assertFalse(is_production_instance({"production": False}))


class ProductionFieldValidationTest(unittest.TestCase):
    def test_non_bool_production_is_rejected(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = "si"
        with self.assertRaises(ValueError):
            _validate_config(config)

    def test_bool_production_is_accepted(self):
        config = _sample_config()
        config["instances"]["acme"]["production"] = True
        _validate_config(config)  # should not raise

    def test_missing_production_is_accepted(self):
        config = _sample_config()
        _validate_config(config)  # should not raise


class DevModeProductionCrossCheckTest(unittest.TestCase):
    def test_dev_mode_rejected_on_production_instance(self):
        config = _sample_config()
        config["odoo_configs"]["base"]["dev_mode"] = True
        config["instances"]["acme"]["production"] = True
        with self.assertRaises(ValueError):
            _validate_config(config)

    def test_dev_mode_allowed_without_production(self):
        config = _sample_config()
        config["odoo_configs"]["base"]["dev_mode"] = True
        _validate_config(config)  # should not raise

    def test_dev_mode_allowed_when_production_explicitly_false(self):
        config = _sample_config()
        config["odoo_configs"]["base"]["dev_mode"] = True
        config["instances"]["acme"]["production"] = False
        _validate_config(config)  # should not raise

    def test_dev_mode_via_instance_override_rejected_on_production(self):
        config = _sample_config()
        config["instances"]["acme"]["overwrite_odoo_config"] = {"dev_mode": True}
        config["instances"]["acme"]["production"] = True
        with self.assertRaises(ValueError):
            _validate_config(config)


if __name__ == "__main__":
    unittest.main()
