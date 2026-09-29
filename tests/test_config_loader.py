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
    resolve_db_bootstrap_creds,
    resolve_db_config,
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


class ResolveDbBootstrapCredsTest(unittest.TestCase):
    """El rol bootstrap DEBE resolverse contra la conf *cruda* del servicio.

    ``resolve_db_config()`` devuelve un dict con ``user``/``password`` ya
    pisados por el rol dedicado de la instancia. Pasarle ese dict a
    ``resolve_db_bootstrap_creds()`` hace que el fallback (``db_conf["user"]``
    cuando el servicio no define ``bootstrap_user``) devuelva el rol de la
    instancia en vez del superusuario del cluster.

    No es teórico: ningún servicio define ``bootstrap_user`` explícito en la
    práctica, así que el fallback se dispara SIEMPRE, y los roles ``app_*``
    son no-superuser por diseño (ver provision_role_sql). El síntoma es un
    "permission denied to alter role" al restaurar un dump que necesita
    CREATE EXTENSION, sin ninguna pista de la causa.
    """

    def _config(self):
        return {
            "databases": {
                "v19": {
                    "user": "odoo",
                    "password": "cluster-pw",
                    "postgres_version": "16",
                }
            },
            "instances": {
                "acme": {
                    "database": "v19",
                    "db_user": "app_acme",
                    "db_password": "acme-pw",
                }
            },
        }

    def test_raw_service_conf_yields_the_cluster_role(self):
        config = self._config()
        raw = config["databases"]["v19"]
        self.assertEqual(
            resolve_db_bootstrap_creds(raw), ("odoo", "cluster-pw")
        )

    def test_resolved_conf_would_leak_the_instance_role(self):
        """Fija el modo de falla, para que quede claro por qué el llamador
        no puede reutilizar el dict de resolve_db_config()."""
        config = self._config()
        resolved = resolve_db_config(config["instances"]["acme"], config)
        self.assertEqual(
            resolve_db_bootstrap_creds(resolved), ("app_acme", "acme-pw")
        )

    def test_explicit_bootstrap_user_wins_over_the_fallback(self):
        config = self._config()
        raw = config["databases"]["v19"]
        raw["bootstrap_user"] = "postgres"
        raw["bootstrap_password"] = "bootstrap-pw"
        self.assertEqual(
            resolve_db_bootstrap_creds(raw), ("postgres", "bootstrap-pw")
        )

    def test_instance_without_dedicated_role_is_unaffected(self):
        config = self._config()
        del config["instances"]["acme"]["db_user"]
        del config["instances"]["acme"]["db_password"]
        resolved = resolve_db_config(config["instances"]["acme"], config)
        self.assertEqual(
            resolve_db_bootstrap_creds(resolved), ("odoo", "cluster-pw")
        )


if __name__ == "__main__":
    unittest.main()
