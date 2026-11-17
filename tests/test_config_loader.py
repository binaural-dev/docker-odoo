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


class DebugValidationTest(unittest.TestCase):
    def cfg(self, **kw):
        from tests.debug_fixtures import debug_config
        c = debug_config(True, False)
        c["instances"]["dbg-a"].update(kw)
        return c

    def test_valid_debug(self):
        _validate_config(self.cfg())
        _validate_config(self.cfg(debug_port=5690))

    def test_debug_must_be_bool(self):
        with self.assertRaises(ValueError):
            _validate_config(self.cfg(debug="si"))

    def test_debug_port_requires_debug_true(self):
        c = self.cfg(debug_port=5690)
        c["instances"]["dbg-a"]["debug"] = False
        with self.assertRaises(ValueError):
            _validate_config(c)

    def test_debug_port_range_and_type(self):
        for bad in (80, 70000, "5690", True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                _validate_config(self.cfg(debug_port=bad))

    def test_debug_port_collides_with_published_ports(self):
        for taken in (28069, 28070, 26000, 80):
            with self.subTest(taken=taken):
                c = self.cfg(debug_port=taken if taken >= 1024 else 5690)
                if taken < 1024:
                    c["instances"]["dbg-a"]["debug_port"] = taken
                with self.assertRaises(ValueError):
                    _validate_config(c)

    def test_debug_port_collides_with_other_debug_port(self):
        c = self.cfg(debug_port=5690)
        c["instances"]["dbg-b"].update(debug=True, debug_port=5690)
        with self.assertRaises(ValueError):
            _validate_config(c)

    def test_debug_rejected_on_production(self):
        with self.assertRaises(ValueError):
            _validate_config(self.cfg(production=True))

    def test_debug_rejected_on_unsupported_version(self):
        c = self.cfg()
        c["instances"]["dbg-a"]["odoo_version"] = "18.0"
        with self.assertRaises(ValueError):
            _validate_config(c)

    def test_restart_validation(self):
        for ok in ("no", "always", "unless-stopped", "on-failure", "on-failure:3"):
            with self.subTest(ok=ok):
                c = self.cfg()
                c["odoo_configs"]["base"]["restart"] = ok
                _validate_config(c)
        c = self.cfg()
        c["odoo_configs"]["base"]["restart"] = "sometimes"
        with self.assertRaises(ValueError):
            _validate_config(c)


class DebugPortsAllocationTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory(prefix="test_dbgports_")
        self.addCleanup(self._tmp.cleanup)
        self.base = self._tmp.name

    def test_sequence_skips_occupied_ports(self):
        from generators.debug_ports import resolve_debug_ports
        from tests.debug_fixtures import debug_config
        c = debug_config(True, True)
        c["databases"]["dbgdb"]["port"] = 5670  # occupied: sequence skips it
        self.assertEqual(
            resolve_debug_ports(self.base, c), {"dbg-a": 5671, "dbg-b": 5672}
        )

    def test_explicit_port_wins_and_is_persisted(self):
        from generators.debug_ports import load_debug_ports, resolve_debug_ports
        from tests.debug_fixtures import debug_config
        c = debug_config(True, True)
        c["instances"]["dbg-b"]["debug_port"] = 5670
        self.assertEqual(
            resolve_debug_ports(self.base, c), {"dbg-a": 5671, "dbg-b": 5670}
        )
        self.assertEqual(load_debug_ports(self.base), {"dbg-a": 5671, "dbg-b": 5670})

    def test_recorded_port_of_inactive_instance_is_reserved(self):
        from generators.debug_ports import resolve_debug_ports
        from tests.debug_fixtures import debug_config
        resolve_debug_ports(self.base, debug_config(True, False))  # a=5670
        out = resolve_debug_ports(self.base, debug_config(False, True))
        self.assertEqual(out, {"dbg-b": 5671})  # 5670 stays reserved for dbg-a

    def test_recorded_port_reassigned_if_now_occupied(self):
        from generators.debug_ports import resolve_debug_ports
        from tests.debug_fixtures import debug_config
        resolve_debug_ports(self.base, debug_config(True, False))
        c = debug_config(True, False)
        c["instances"]["dbg-b"]["external_port"] = 5670
        self.assertEqual(resolve_debug_ports(self.base, c), {"dbg-a": 5671})

    def test_corrupt_ports_file_is_ignored(self):
        from generators.debug_ports import ports_path, resolve_debug_ports
        from tests.debug_fixtures import debug_config
        os.makedirs(os.path.dirname(ports_path(self.base)))
        with open(ports_path(self.base), "w") as f:
            f.write("{not json")
        self.assertEqual(resolve_debug_ports(self.base, debug_config(True, False)), {"dbg-a": 5670})

    def test_prune_forgets_inactive(self):
        from generators.debug_ports import load_debug_ports, prune_debug_ports, resolve_debug_ports
        from tests.debug_fixtures import debug_config
        resolve_debug_ports(self.base, debug_config(True, True))
        self.assertEqual(prune_debug_ports(self.base, debug_config(False, True)), ["dbg-a"])
        self.assertEqual(load_debug_ports(self.base), {"dbg-b": 5671})


if __name__ == "__main__":
    unittest.main()
