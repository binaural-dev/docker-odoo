#!/usr/bin/env python3
"""Tests para el chequeo de returncode de psql en reset_password.

Bug original: subprocess.run no se chequeaba, asi que psql fallaba
silencioso y el script reportaba 'exito' igual. Estos tests verifican
que (a) returncode != 0 aborta con sys.exit y (b) returncode == 0
imprime '✅ Contraseña actualizada.'

Cubren tanto el wrapper de odoo (reset_password) como el script
standalone scripts/odoo-pw.
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
    """Carga odoo como modulo importable (sin ejecutar main)."""
    loader = SourceFileLoader("_odoo_pw_under_test", str(ODOO_WRAPPER))
    spec = importlib.util.spec_from_loader("_odoo_pw_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_odoo_pw_under_test"] = mod
    loader.exec_module(mod)
    return mod


def _make_config(instance="inst1", dbname="pg16"):
    """Config minimo para reset_password/odoo-pw."""
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


class OdooPwReturncodeTest(unittest.TestCase):
    """Suite de regresion para el chequeo de returncode."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_odoo_wrapper()

    # ------------------------------------------------------------------
    # reset_password (en odoo) — flujo feliz y fallo
    # ------------------------------------------------------------------

    def test_reset_password_success(self):
        """returncode == 0 -> imprime '✅ Contraseña actualizada.' y NO aborta."""
        config = _make_config()
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            # Bypass el chequeo de existencia de DB (probado en
            # test_pw_db_validation.py) y centrar el test en el
            # comportamiento de returncode.
            with mock.patch.object(self.mod, "_check_db_exists",
                                   return_value=(True, [])):
                with mock.patch.object(subprocess, "run") as mock_run:
                    mock_run.return_value = subprocess.CompletedProcess(
                        args=[], returncode=0, stdout="", stderr="",
                    )
                    try:
                        self.mod.reset_password(
                            config, "inst1", "rea", "admin", "admin",
                        )
                        exit_code = 0
                    except SystemExit as e:
                        exit_code = e.code
        out = buf_out.getvalue()
        self.assertEqual(exit_code, 0, f"reset_password aborte con rc={exit_code}")
        self.assertIn("✅", out, "no se imprime el emoji de exito en flujo feliz")
        self.assertIn("Contraseña actualizada", out)
        self.assertNotIn("NO actualizada", out)
        mock_run.assert_called_once()

    def test_reset_password_psql_failure_aborts(self):
        """returncode != 0 -> sys.exit(returncode) y NO imprime '✅'."""
        config = _make_config()
        buf_out, buf_err = io.StringIO(), io.StringIO()
        exit_code = None
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            with mock.patch.object(self.mod, "_check_db_exists",
                                   return_value=(True, [])):
                with mock.patch.object(subprocess, "run") as mock_run:
                    mock_run.return_value = subprocess.CompletedProcess(
                        args=[], returncode=1, stdout="", stderr="FATAL",
                    )
                    try:
                        self.mod.reset_password(
                            config, "inst1", "rea", "admin", "admin",
                        )
                        exit_code = 0
                    except SystemExit as e:
                        exit_code = e.code
        self.assertEqual(
            exit_code, 1,
            f"reset_password NO aborte con rc=1 (got {exit_code})",
        )
        out = buf_out.getvalue()
        self.assertNotIn(
            "✅ Contraseña actualizada", out,
            f"BUG: se imprimio el exito falso en flujo fallido:\n{out}",
        )
        self.assertIn("Error ejecutando psql", out)
        self.assertIn("NO actualizada", out)

    def test_reset_password_psql_failure_nonzero_propagates(self):
        """returncode != 0 con valor arbitrario -> sys.exit(returncode)."""
        config = _make_config()
        exit_code = None
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with mock.patch.object(self.mod, "_check_db_exists",
                                   return_value=(True, [])):
                with mock.patch.object(subprocess, "run") as mock_run:
                    mock_run.return_value = subprocess.CompletedProcess(
                        args=[], returncode=42, stdout="", stderr="",
                    )
                    try:
                        self.mod.reset_password(
                            config, "inst1", "rea", "admin", "admin",
                        )
                    except SystemExit as e:
                        exit_code = e.code
        self.assertEqual(
            exit_code, 42,
            f"reset_password propago rc=42? got {exit_code}",
        )

    # ------------------------------------------------------------------
    # scripts/odoo-pw — flujo feliz y fallo (vía click CliRunner)
    # ------------------------------------------------------------------

    def test_odoo_pw_script_success(self):
        """scripts/odoo-pw: rc=0 -> imprime '✅' y exit code 0."""
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
             ), \
             mock.patch(
                 "generators.pw_helpers._check_db_exists",
                 return_value=(True, []),
                 create=True,
             ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            )
            loader = SourceFileLoader("_odoo_pw_script", str(ODOO_PW_SCRIPT))
            spec = importlib.util.spec_from_loader("_odoo_pw_script", loader)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_odoo_pw_script"] = mod
            loader.exec_module(mod)
            # `run_command` ahora es un click.Command (decorado).
            runner = CliRunner()
            result = runner.invoke(
                mod.run_command,
                ["inst1", "-d", "rea", "-l", "admin"],
                catch_exceptions=False,
            )
        self.assertEqual(
            result.exit_code, 0,
            f"scripts/odoo-pw aborte en flujo feliz: {result.exit_code}\n"
            f"output: {result.output}",
        )
        self.assertIn("✅", result.output)
        self.assertIn("Contraseña actualizada", result.output)
        self.assertNotIn("NO actualizada", result.output)
        mock_run.assert_called_once()

    def test_odoo_pw_script_psql_failure_aborts(self):
        """scripts/odoo-pw: rc != 0 -> exit_code=1 y NO imprime '✅'."""
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
             ), \
             mock.patch(
                 "generators.pw_helpers._check_db_exists",
                 return_value=(True, []),
                 create=True,
             ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="FATAL",
            )
            loader = SourceFileLoader("_odoo_pw_script_v2", str(ODOO_PW_SCRIPT))
            spec = importlib.util.spec_from_loader("_odoo_pw_script_v2", loader)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_odoo_pw_script_v2"] = mod
            loader.exec_module(mod)
            runner = CliRunner()
            result = runner.invoke(
                mod.run_command,
                ["inst1", "-d", "rea", "-l", "admin"],
                catch_exceptions=False,
            )
        self.assertEqual(
            result.exit_code, 1,
            f"scripts/odoo-pw NO aborte con rc=1: {result.exit_code}\n"
            f"output: {result.output}",
        )
        self.assertNotIn(
            "✅ Contraseña actualizada", result.output,
            f"BUG: scripts/odoo-pw imprimio exito falso:\n{result.output}",
        )
        self.assertIn("Error ejecutando psql", result.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("unittest_args", nargs="*")
    parsed, _ = parser.parse_known_args()
    argv = [sys.argv[0]] + (["-v"] if parsed.verbose else []) + parsed.unittest_args
    unittest.main(argv=argv, verbosity=2 if parsed.verbose else 1, exit=False)
