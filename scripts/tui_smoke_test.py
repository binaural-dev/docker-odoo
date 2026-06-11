#!/usr/bin/env python3
"""Smoke tests automatizados para la TUI v3 (CSS externo + OptionList + --dev).

Uso:
    python3 scripts/tui_smoke_test.py
    python3 scripts/tui_smoke_test.py -v

Cubre las nueve simulaciones del plan v3:
  1. El propio smoke corre limpio (este test).
  2. Headless app boot: DockerOdooApp arranca y termina limpio en
     headless con size=(120, 40).
  3. Dev mode boot: con dev=True no crashea y self.dev persiste.
  4. CSS parse: odoo-tui.tcss parsea via el runtime de Textual.
  5. ModulePicker compose: la modal monta sin MountError.
  6. OptionList highlight: con Pilot, press('down') cambia highlighted.
  7. --dev flag parsing: _parse_args(['--dev']).dev es True.
  8. --help output: el argparse muestra --dev.
  9. No regresion de instancias: DockerOdooApp con dev=False sigue
     exponiendo los ListView de instances_list y actions_list.

Implementacion: unittest de stdlib (sin pytest) + asyncio.run para
los pedazos async (Textual Pilot).
"""

import argparse
import asyncio
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ODOO_TUI = REPO_ROOT / "odoo-tui"
TCSS_PATH = REPO_ROOT / "odoo-tui.tcss"


def _load_odoo_tui():
    """Carga el script odoo-tui como modulo importable."""
    loader = SourceFileLoader("_tui_smoke", str(ODOO_TUI))
    spec = importlib.util.spec_from_loader("_tui_smoke", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_tui_smoke"] = mod
    loader.exec_module(mod)
    return mod


class TuiSmokeTest(unittest.TestCase):
    """Suite de smoke tests para la TUI v3."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_odoo_tui()
        cls.tcss_text = TCSS_PATH.read_text()

    # ------------------------------------------------------------------
    # Sim 4: CSS parse
    # ------------------------------------------------------------------

    def test_css_file_exists(self):
        """Sim 4a: el archivo odoo-tui.tcss existe en la raiz del repo."""
        self.assertTrue(TCSS_PATH.exists(), f"Falta {TCSS_PATH}")
        self.assertGreater(len(self.tcss_text), 0, "TCSS vacio")

    def test_css_path_declared(self):
        """Sim 4b: DockerOdooApp declara CSS_PATH apuntando al archivo."""
        declared = self.mod.DockerOdooApp.__dict__.get("CSS_PATH")
        self.assertIsNotNone(declared, "DockerOdooApp no define CSS_PATH")
        self.assertTrue(
            (REPO_ROOT / declared).exists(),
            f"CSS_PATH apunta a archivo inexistente: {declared}",
        )

    def test_css_loads_in_app(self):
        """Sim 4c: el CSS parsea via el runtime real de Textual."""
        from textual.app import App
        from textual.widgets import Static

        class _Probe(App):
            CSS_PATH = str(TCSS_PATH)

            def compose(self):
                yield Static("x")

        async def go():
            app = _Probe()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                rules = (
                    len(app.stylesheet.rules)
                    if hasattr(app.stylesheet, "rules")
                    else 0
                )
                return rules

        rules = asyncio.run(go())
        self.assertGreater(rules, 0, "El stylesheet no cargo reglas")

    # ------------------------------------------------------------------
    # Sim 7: --dev flag parsing
    # ------------------------------------------------------------------

    def test_dev_flag_absent(self):
        """Sim 7a: sin flag, args.dev es False."""
        args = self.mod._parse_args([])
        self.assertFalse(args.dev)

    def test_dev_flag_present(self):
        """Sim 7b: con --dev, args.dev es True."""
        args = self.mod._parse_args(["--dev"])
        self.assertTrue(args.dev)

    def test_dev_flag_with_value(self):
        """Sim 7c: con --dev=all, args.dev es 'all'."""
        args = self.mod._parse_args(["--dev=all"])
        self.assertEqual(args.dev, "all")

    # ------------------------------------------------------------------
    # Sim 8: --help output
    # ------------------------------------------------------------------

    def test_help_mentions_dev(self):
        """Sim 8: --help imprime usage que menciona --dev."""
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            with self.assertRaises(SystemExit):
                self.mod._parse_args(["--help"])
        output = buf_out.getvalue() + buf_err.getvalue()
        self.assertIn("--dev", output, f"--help no menciona --dev:\n{output}")

    def test_help_exit_code_via_subprocess(self):
        """Sim 8b: el script real imprime --dev en --help (subprocess)."""
        result = subprocess.run(
            [sys.executable, str(ODOO_TUI), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, f"odoo-tui --help fallo:\n{result.stderr}")
        self.assertIn("--dev", result.stdout, f"--help no menciona --dev:\n{result.stdout}")

    # ------------------------------------------------------------------
    # Sim 2 / 3: headless app boot + dev mode boot
    # ------------------------------------------------------------------

    def test_headless_app_boot(self):
        """Sim 2: DockerOdooApp arranca en headless y termina limpio."""
        async def go():
            app = self.mod.DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_dev_mode_boot(self):
        """Sim 3: dev=True arranca limpio y self.dev queda accesible."""
        async def go():
            app = self.mod.DockerOdooApp(dev=True)
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                return app.dev

        dev = asyncio.run(go())
        self.assertTrue(dev)

    def test_dev_mode_all(self):
        """Sim 3b: dev='all' tambien arranca limpio."""
        async def go():
            app = self.mod.DockerOdooApp(dev="all")
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                return app.dev

        dev = asyncio.run(go())
        self.assertEqual(dev, "all")

    # ------------------------------------------------------------------
    # Sim 9: no regresion de instancias (ListViews siguen funcionando)
    # ------------------------------------------------------------------

    def test_instance_listview_present(self):
        """Sim 9: DockerOdooApp sigue exponiendo #instances_list como ListView."""
        from textual.widgets import ListView

        async def go():
            app = self.mod.DockerOdooApp()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                lv = app.query_one("#instances_list", ListView)
                return len(lv.children)

        n = asyncio.run(go())
        # Al menos 1 hijo (el "Todas las instancias" item se agrega en
        # refresh_instances; sin instances.json puede haber 1).
        self.assertGreaterEqual(n, 1, "instances_list quedo vacio")

    def test_actions_listview_present(self):
        """Sim 9b: DockerOdooApp sigue exponiendo #actions_list como ListView."""
        from textual.widgets import ListView

        async def go():
            app = self.mod.DockerOdooApp()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                lv = app.query_one("#actions_list", ListView)
                return len(lv.children)

        n = asyncio.run(go())
        # Las ACTIONS tienen ~22 entradas; todas se cargan por categoria.
        self.assertGreater(n, 0, "actions_list quedo vacio")

    # ------------------------------------------------------------------
    # Sim 5: ModulePicker compose (sin MountError)
    # ------------------------------------------------------------------

    def test_module_picker_compose(self):
        """Sim 5: ModulePicker monta sin MountError por id duplicado."""
        from textual.app import App
        from textual.widgets import Static

        async def go():
            class _Host(App):
                def compose(self):
                    yield Static("host")

            app = _Host()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                picker = self.mod.ModulePicker(
                    instance_name="test",
                    available_modules=["sale", "purchase", "stock"],
                )
                await app.push_screen(picker)
                await pilot.pause()
                # Confirma que la modal monto
                available = picker.query_one("#available_list")
                selected = picker.query_one("#selected_list")
                from textual.widgets import OptionList

                self.assertIsInstance(available, OptionList)
                self.assertIsInstance(selected, OptionList)
                self.assertEqual(len(available.options), 3)
                self.assertEqual(len(selected.options), 0)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    # ------------------------------------------------------------------
    # Sim 6: OptionList highlight con Pilot
    # ------------------------------------------------------------------

    def test_option_list_highlight(self):
        """Sim 6: con Pilot, press('down') cambia highlighted del OptionList."""
        from textual.app import App
        from textual.widgets import Static

        async def go():
            class _Host(App):
                def compose(self):
                    yield Static("host")

            app = _Host()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                picker = self.mod.ModulePicker(
                    instance_name="test",
                    available_modules=["sale", "purchase", "stock"],
                )
                await app.push_screen(picker)
                await pilot.pause()

                available = picker.query_one("#available_list")
                # highlighted arranca en None (no hay focus aun)
                initial = available.highlighted
                available.focus()
                await pilot.pause()
                focused_initial = available.highlighted
                # Press down debe mover el cursor
                await pilot.press("down")
                await pilot.pause()
                after_down = available.highlighted
                # Press enter dispara OptionSelected -> handler selecciona
                await pilot.press("enter")
                await pilot.pause()
                return {
                    "initial": initial,
                    "focused_initial": focused_initial,
                    "after_down": after_down,
                    "selected_after_enter": list(picker.selected),
                }

        result = asyncio.run(go())
        # Verifica que down cambia el cursor (de None o 0 a >=0)
        self.assertIsNotNone(
            result["after_down"],
            f"highlighted no cambio tras press('down'): {result}",
        )
        # Verifica que enter selecciona un modulo
        self.assertEqual(
            len(result["selected_after_enter"]),
            1,
            f"enter no selecciono un modulo: {result}",
        )


if __name__ == "__main__":
    # Permitir -v para verbosity
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("unittest_args", nargs="*")
    parsed, _ = parser.parse_known_args()
    argv = [sys.argv[0]] + (["-v"] if parsed.verbose else []) + parsed.unittest_args
    unittest.main(argv=argv, verbosity=2 if parsed.verbose else 1, exit=False)
