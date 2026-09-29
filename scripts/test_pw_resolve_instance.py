#!/usr/bin/env python3
"""Tests para _resolve_instance_for_action (commit 3 del fix).

Bug original: el pre-dispatch (odoo:770) siempre pedia instancia
para 'pw' si no se paso posicional, incluso si el usuario paso '-d
<dbname>'. El usuario pensaba que '-d rea' era suficiente, le pedian
instancia de todos modos, elegia cualquiera y terminaba apuntando
a la DB incorrecta.

Solucion probada aca: _resolve_instance_for_action busca en todas
las instancias cual tiene la DB pasada en '-d'. Comportamientos:

  Caso 1: args.d = None             -> prompt_for_instance (legacy).
  Caso 2: 0 matches                 -> prompt_for_instance (legacy).
  Caso 3: 1 match                   -> devuelve la instancia sin prompt.
  Caso 4: 2+ matches                -> prompt_selection con candidatas.
  Caso 5: args.instance posicional  -> lo devuelve sin chequear DBs.
"""

import argparse
import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
ODOO_WRAPPER = REPO_ROOT / "odoo"


def _load_odoo_wrapper():
    loader = SourceFileLoader("_odoo_resolve_under_test", str(ODOO_WRAPPER))
    spec = importlib.util.spec_from_loader("_odoo_resolve_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_odoo_resolve_under_test"] = mod
    loader.exec_module(mod)
    return mod


def _make_config(n_instancias=2):
    """Config minimo con N instancias que comparten el mismo DB."""
    return {
        "instances": {
            f"inst{i}": {
                "odoo_version": "17.0",
                "database": "pg16",
            }
            for i in range(1, n_instancias + 1)
        },
        "databases": {
            "pg16": {
                "postgres_version": 17,
                "port": 5432,
                "user": "odoo",
                "password": "odoo",
            }
        },
    }


def _db_check_response(has_db):
    """Simula SELECT 1 FROM pg_database -> 1 fila o ninguna."""
    stdout = "1\n" if has_db else "\n"
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr="",
    )


class ResolveInstanceTest(unittest.TestCase):
    """Suite de regresion para _resolve_instance_for_action."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_odoo_wrapper()

    def _args(self, action="pw", instance=None, d=None):
        return argparse.Namespace(action=action, instance=instance, d=d)

    # ------------------------------------------------------------------
    # Caso 1: args.d = None -> prompt_for_instance (legacy)
    # Caso 5: args.instance posicional -> se devuelve tal cual
    # ------------------------------------------------------------------

    def test_no_db_uses_prompt(self):
        """Caso 1: sin -d, debe llamar prompt_for_instance (legacy)."""
        config = _make_config()
        with mock.patch.object(self.mod, "prompt_for_instance",
                               return_value="inst1") as mock_prompt:
            with mock.patch.object(self.mod, "prompt_selection") as mock_sel, \
                 mock.patch.object(self.mod, "_instance_has_db",
                                   return_value=True) as mock_check:
                result = self.mod._resolve_instance_for_action(
                    config, self._args(action="pw", d=None),
                )
        self.assertEqual(result, "inst1")
        mock_prompt.assert_called_once_with(config, "pw")
        # No se chequean DBs si no se paso -d.
        mock_check.assert_not_called()
        mock_sel.assert_not_called()

    def test_instance_positional_returned_as_is(self):
        """Caso 5: instance posicional -> se devuelve, no se hace nada."""
        config = _make_config()
        with mock.patch.object(self.mod, "prompt_for_instance") as mock_prompt, \
             mock.patch.object(self.mod, "_instance_has_db") as mock_check, \
             mock.patch.object(self.mod, "prompt_selection") as mock_sel:
            result = self.mod._resolve_instance_for_action(
                config, self._args(action="pw", instance="inst2", d="rea"),
            )
        self.assertEqual(result, "inst2")
        # No se hace nada mas cuando instance ya esta seteado.
        mock_prompt.assert_not_called()
        mock_check.assert_not_called()
        mock_sel.assert_not_called()

    # ------------------------------------------------------------------
    # Caso 2: 0 matches -> prompt_for_instance
    # ------------------------------------------------------------------

    def test_zero_matches_falls_back_to_prompt(self):
        """Caso 2: ninguna instancia tiene la DB -> prompt_for_instance."""
        config = _make_config(n_instancias=2)
        with mock.patch.object(self.mod, "prompt_for_instance",
                               return_value="inst1") as mock_prompt, \
             mock.patch.object(self.mod, "_instance_has_db",
                               return_value=False) as mock_check, \
             mock.patch.object(self.mod, "prompt_selection") as mock_sel:
            result = self.mod._resolve_instance_for_action(
                config, self._args(action="pw", d="rea"),
            )
        self.assertEqual(result, "inst1")
        mock_check.assert_called()
        mock_prompt.assert_called_once_with(config, "pw")
        mock_sel.assert_not_called()

    # ------------------------------------------------------------------
    # Caso 3: 1 match -> devuelve esa instancia sin prompt
    # ------------------------------------------------------------------

    def test_one_match_no_prompt(self):
        """Caso 3: una sola instancia tiene la DB -> la usa sin prompt."""
        config = _make_config(n_instancias=3)

        def fake_has_db(instance, dbname, _config):
            return instance == "inst2"

        with mock.patch.object(self.mod, "prompt_for_instance") as mock_prompt, \
             mock.patch.object(self.mod, "_instance_has_db",
                               side_effect=fake_has_db), \
             mock.patch.object(self.mod, "prompt_selection") as mock_sel:
            result = self.mod._resolve_instance_for_action(
                config, self._args(action="pw", d="rea"),
            )
        self.assertEqual(result, "inst2")
        mock_prompt.assert_not_called()
        mock_sel.assert_not_called()

    # ------------------------------------------------------------------
    # Caso 4: 2+ matches -> prompt_selection con candidatas
    # ------------------------------------------------------------------

    def test_multiple_matches_prompts_with_candidates(self):
        """Caso 4: >1 instancia tiene la DB -> prompt con candidatas."""
        config = _make_config(n_instancias=3)

        def fake_has_db(instance, dbname, _config):
            return instance in ("inst1", "inst3")

        with mock.patch.object(self.mod, "prompt_for_instance") as mock_prompt, \
             mock.patch.object(self.mod, "_instance_has_db",
                               side_effect=fake_has_db), \
             mock.patch.object(self.mod, "prompt_selection",
                               return_value="inst3") as mock_sel:
            result = self.mod._resolve_instance_for_action(
                config, self._args(action="pw", d="rea"),
            )
        self.assertEqual(result, "inst3")
        mock_prompt.assert_not_called()
        # Se invoca prompt_selection con las candidatas correctas.
        mock_sel.assert_called_once()
        options_arg = mock_sel.call_args.args[0]
        # options_arg es lista de tuplas (label, value).
        labels = [t[0] for t in options_arg]
        values = [t[1] for t in options_arg]
        self.assertEqual(set(values), {"inst1", "inst3"})
        self.assertNotIn("inst2", values)
        # El titulo menciona la DB.
        title = mock_sel.call_args.args[1]
        self.assertIn("rea", title)

    # ------------------------------------------------------------------
    # Caso adicional: otra accion (no pw) -> no consulta DBs
    # ------------------------------------------------------------------

    def test_other_action_no_db_lookup(self):
        """Para 'start' (no pw), no se consulta la DB aunque este '-d'."""
        config = _make_config()
        with mock.patch.object(self.mod, "prompt_for_instance",
                               return_value="inst1") as mock_prompt, \
             mock.patch.object(self.mod, "prompt_selection") as mock_sel, \
             mock.patch.object(self.mod, "_instance_has_db") as mock_check:
            result = self.mod._resolve_instance_for_action(
                config, self._args(action="start", d="rea"),
            )
        self.assertEqual(result, "inst1")
        mock_prompt.assert_called_once_with(config, "start")
        mock_check.assert_not_called()
        mock_sel.assert_not_called()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("unittest_args", nargs="*")
    parsed, _ = parser.parse_known_args()
    argv = [sys.argv[0]] + (["-v"] if parsed.verbose else []) + parsed.unittest_args
    unittest.main(argv=argv, verbosity=2 if parsed.verbose else 1, exit=False)
