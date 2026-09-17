#!/usr/bin/env python3
"""Tests para la validacion de existencia de DB en odoo:reset_password
y scripts/odoo-pw.

Bug original: si el usuario pasaba -d <dbname> apuntando a una DB
que no existia en la instancia, psql fallaba con 'database does
not exist' y el script no se enteraba (ver test_pw_returncode.py
para el lado de returncode). Aqui probamos que el chequeo previo
via _check_db_exists:

  - Si la DB existe -> no aborta, continua al UPDATE.
  - Si NO existe -> aborta con sys.exit(1) y mensaje claro,
    listando las bases disponibles en la instancia.
"""

import argparse
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
ODOO_WRAPPER = REPO_ROOT / "odoo"
ODOO_PW_SCRIPT = REPO_ROOT / "scripts" / "odoo-pw"


def _load_odoo_wrapper():
    loader = SourceFileLoader("_odoo_pw_db_under_test", str(ODOO_WRAPPER))
    spec = importlib.util.spec_from_loader("_odoo_pw_db_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_odoo_pw_db_under_test"] = mod
    loader.exec_module(mod)
    return mod


def _make_config(instance="inst1", dbname="pg16"):
    return {
        "instances": {
            instance: {
                "odoo_version": "17.0",
                "database": dbname,
            }
        },
        "databases": {
            dbname: {
                "postgres_version": 17,
                "port": 5432,
                "user": "odoo",
                "password": "odoo",
            }
        },
    }


def _db_exists_ok(*args, **kwargs):
    """Respuesta simulada: DB existe."""
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout="1\n", stderr="",
    )


def _db_listing_ok(*args, **kwargs):
    """Respuesta simulada: lista de DBs disponibles."""
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout="postgres\nrea\nodoo\n", stderr="",
    )


def _db_missing(*args, **kwargs):
    """Respuesta simulada: DB no aparece en la primera consulta."""
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout="\n", stderr="",
    )


class OdooPwDbValidationTest(unittest.TestCase):
    """Suite de regresion para el chequeo de existencia de DB."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_odoo_wrapper()

    # ------------------------------------------------------------------
    # reset_password (odoo) — DB existe, DB no existe
    # ------------------------------------------------------------------

    def test_reset_password_db_exists_continues(self):
        """Si la DB existe, el UPDATE corre y se imprime '✅'."""
        config = _make_config()
        buf_out = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(io.StringIO()):
            with mock.patch.object(subprocess, "run") as mock_run:
                # 1ra llamada: _check_db_exists -> SELECT 1
                # 2da llamada: UPDATE en res_users
                mock_run.side_effect = [_db_exists_ok(),
                                        _db_exists_ok()]
                try:
                    self.mod.reset_password(
                        config, "inst1", "rea", "admin", "admin",
                    )
                    exit_code = 0
                except SystemExit as e:
                    exit_code = e.code
        out = buf_out.getvalue()
        self.assertEqual(
            exit_code, 0,
            f"reset_password aborte con DB existente: {exit_code}\n{out}",
        )
        self.assertIn("✅", out)
        self.assertIn("Contraseña actualizada", out)
        # 2 llamadas a psql: check + update
        self.assertEqual(mock_run.call_count, 2)

    def test_reset_password_db_missing_aborts_before_update(self):
        """Si la DB NO existe, aborta con sys.exit(1) y NO corre el UPDATE."""
        config = _make_config()
        buf_out = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(io.StringIO()):
            with mock.patch.object(subprocess, "run") as mock_run:
                # 1ra: check -> 0 filas; 2da: listing -> DBs disponibles
                # 3ra llamada (el UPDATE) NO debe ocurrir.
                mock_run.side_effect = [_db_missing(), _db_listing_ok()]
                try:
                    self.mod.reset_password(
                        config, "inst1", "rea", "admin", "admin",
                    )
                    exit_code = 0
                except SystemExit as e:
                    exit_code = e.code
        out = buf_out.getvalue()
        self.assertEqual(
            exit_code, 1,
            f"reset_password NO aborte con DB faltante: {exit_code}",
        )
        self.assertNotIn("✅", out, f"BUG: exito falso en flujo fallido:\n{out}")
        self.assertIn("no existe en la instancia", out)
        self.assertIn("Bases disponibles", out)
        self.assertIn("rea", out)  # La lista de DBs aparece en el mensaje
        # Exactamente 2 llamadas a psql: check + listing. NO update.
        self.assertEqual(
            mock_run.call_count, 2,
            f"se llamo psql {mock_run.call_count} veces (esperaba 2):\n"
            f"calls: {mock_run.call_args_list}",
        )

    # ------------------------------------------------------------------
    # scripts/odoo-pw — DB existe, DB no existe
    # ------------------------------------------------------------------

    def test_odoo_pw_script_db_exists_continues(self):
        """scripts/odoo-pw: DB existe -> imprime '✅' y exit 0."""
        try:
            from click.testing import CliRunner
        except ImportError:
            self.skipTest("click no disponible")

        config = _make_config()
        with mock.patch.object(subprocess, "run") as mock_run, \
             mock.patch(
                 "generators.config_loader.load_config",
                 return_value=config,
                 create=True,
             ):
            mock_run.side_effect = [_db_exists_ok(), _db_exists_ok()]
            loader = SourceFileLoader("_odoo_pw_db_script", str(ODOO_PW_SCRIPT))
            spec = importlib.util.spec_from_loader("_odoo_pw_db_script", loader)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_odoo_pw_db_script"] = mod
            loader.exec_module(mod)
            runner = CliRunner()
            result = runner.invoke(
                mod.run_command,
                ["inst1", "-d", "rea", "-l", "admin"],
                catch_exceptions=False,
            )
        self.assertEqual(
            result.exit_code, 0,
            f"scripts/odoo-pw aborte con DB existente: {result.exit_code}\n"
            f"output: {result.output}",
        )
        self.assertIn("✅", result.output)
        self.assertIn("Contraseña actualizada", result.output)
        self.assertEqual(mock_run.call_count, 2)

    def test_odoo_pw_script_db_missing_aborts(self):
        """scripts/odoo-pw: DB NO existe -> exit 1, NO imprime '✅'."""
        try:
            from click.testing import CliRunner
        except ImportError:
            self.skipTest("click no disponible")

        config = _make_config()
        with mock.patch.object(subprocess, "run") as mock_run, \
             mock.patch(
                 "generators.config_loader.load_config",
                 return_value=config,
                 create=True,
             ):
            mock_run.side_effect = [_db_missing(), _db_listing_ok()]
            loader = SourceFileLoader("_odoo_pw_db_script_v2", str(ODOO_PW_SCRIPT))
            spec = importlib.util.spec_from_loader("_odoo_pw_db_script_v2", loader)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_odoo_pw_db_script_v2"] = mod
            loader.exec_module(mod)
            runner = CliRunner()
            result = runner.invoke(
                mod.run_command,
                ["inst1", "-d", "rea", "-l", "admin"],
                catch_exceptions=False,
            )
        self.assertEqual(
            result.exit_code, 1,
            f"scripts/odoo-pw NO aborte con DB faltante: {result.exit_code}\n"
            f"output: {result.output}",
        )
        self.assertNotIn(
            "✅ Contraseña actualizada", result.output,
            f"BUG: exito falso en flujo fallido:\n{result.output}",
        )
        self.assertIn("no existe en la instancia", result.output)
        self.assertIn("Bases disponibles", result.output)
        # Solo check + listing; NO update
        self.assertEqual(
            mock_run.call_count, 2,
            f"se llamo psql {mock_run.call_count} veces (esperaba 2)",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("unittest_args", nargs="*")
    parsed, _ = parser.parse_known_args()
    argv = [sys.argv[0]] + (["-v"] if parsed.verbose else []) + parsed.unittest_args
    unittest.main(argv=argv, verbosity=2 if parsed.verbose else 1, exit=False)
