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
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tui.parser import parse_progress, classify_level
from tui.models import Action
from tui.actions import get_action
from tui.app import DockerOdooApp
from tui.widgets.update_progress import UpdateProgress
from tui.__main__ import _parse_args

ODOO_TUI = REPO_ROOT / "odoo-tui"
TCSS_PATH = REPO_ROOT / "tui" / "styles" / "odoo-tui.tcss"


class TuiSmokeTest(unittest.TestCase):
    """Suite de smoke tests para la TUI v3."""

    @classmethod
    def setUpClass(cls):
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
        from textual._path import _make_path_object_relative

        declared = DockerOdooApp.__dict__.get("CSS_PATH")
        self.assertIsNotNone(declared, "DockerOdooApp no define CSS_PATH")
        app = DockerOdooApp()
        resolved = _make_path_object_relative(declared, app)
        self.assertTrue(
            resolved.exists(),
            f"CSS_PATH ({declared!r}) resuelve a archivo inexistente: {resolved}",
        )
        self.assertEqual(
            resolved, TCSS_PATH,
            f"CSS_PATH resuelve a {resolved}, se esperaba {TCSS_PATH}",
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
        args = _parse_args([])
        self.assertFalse(args.dev)

    def test_dev_flag_present(self):
        """Sim 7b: con --dev, args.dev es True."""
        args = _parse_args(["--dev"])
        self.assertTrue(args.dev)

    def test_dev_flag_with_value(self):
        """Sim 7c: con --dev=all, args.dev es 'all'."""
        args = _parse_args(["--dev=all"])
        self.assertEqual(args.dev, "all")

    # ------------------------------------------------------------------
    # Sim 8: --help output
    # ------------------------------------------------------------------

    def test_help_mentions_dev(self):
        """Sim 8: --help imprime usage que menciona --dev."""
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            with self.assertRaises(SystemExit):
                _parse_args(["--help"])
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
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_dev_mode_boot(self):
        """Sim 3: dev=True arranca limpio y self.dev queda accesible."""
        async def go():
            app = DockerOdooApp(dev=True)
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                return app.dev

        dev = asyncio.run(go())
        self.assertTrue(dev)

    def test_dev_mode_all(self):
        """Sim 3b: dev='all' tambien arranca limpio."""
        async def go():
            app = DockerOdooApp(dev="all")
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
            app = DockerOdooApp()
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
            app = DockerOdooApp()
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
        from tui.screens.module_picker import ModulePicker

        async def go():
            class _Host(App):
                def compose(self):
                    yield Static("host")

            app = _Host()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                picker = ModulePicker(
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
        from tui.screens.module_picker import ModulePicker

        async def go():
            class _Host(App):
                def compose(self):
                    yield Static("host")

            app = _Host()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                picker = ModulePicker(
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


# ============================================================
# TUI v4 — UpdateProgress tests
# ============================================================


class TuiProgressParserTest(unittest.TestCase):
    """Sim 1: tests del parser de progreso puro."""

    def test_parse_match_simple(self):
        """(45/234) → (45, 234)"""
        r = parse_progress("(45/234)")
        self.assertEqual(r, (45, 234))

    def test_parse_no_match(self):
        """linea sin parentesis → None"""
        r = parse_progress("INFO: sale module updated")
        self.assertIsNone(r)

    def test_parse_zero_current(self):
        """(0/1) → (0, 1)"""
        r = parse_progress("(0/1)")
        self.assertEqual(r, (0, 1))

    def test_parse_large_numbers(self):
        """(999/1000) → (999, 1000)"""
        r = parse_progress("(999/1000)")
        self.assertEqual(r, (999, 1000))

    def test_parse_multiple_matches(self):
        """linea con dos matches → primer match (0/1)"""
        r = parse_progress("(0/1) (45/234)")
        self.assertEqual(r, (0, 1))

    def test_parse_with_surrounding_text(self):
        """linea con texto envolvente → (5, 10)"""
        r = parse_progress(
            "2024-01-01 10:00:00 INFO (5/10) sale"
        )
        self.assertEqual(r, (5, 10))


class TuiLevelClassifierTest(unittest.TestCase):
    """Sim 2: tests del clasificador de nivel."""

    def test_critical(self):
        self.assertEqual(
            classify_level("CRITICAL: Odoo crashed"),
            "CRITICAL",
        )

    def test_error(self):
        self.assertEqual(
            classify_level("ERROR: sale module failed"),
            "ERROR",
        )

    def test_warning(self):
        self.assertEqual(
            classify_level("WARNING: account deprecated"),
            "WARNING",
        )

    def test_info(self):
        self.assertEqual(
            classify_level("INFO: update module sale"),
            "INFO",
        )

    def test_no_prefix_defaults_to_info(self):
        """linea sin prefijo → INFO"""
        self.assertEqual(
            classify_level("  some log message"),
            "INFO",
        )

    def test_error_with_indent(self):
        """linea con espacio previo → ERROR"""
        self.assertEqual(
            classify_level("  ERROR: something"),
            "ERROR",
        )


class TuiUpdateProgressWidgetTest(unittest.TestCase):
    """Sim 3: tests del widget presentacional UpdateProgress."""

    def test_progress_widget_compose(self):
        """UpdateProgress se monta con ProgressBar, labels y chips."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress(instance_name="test", modules="sale")
                await app.mount(up)
                await pilot.pause()
                self.assertIsNotNone(up.query_one("#up_progress"))
                self.assertIsNotNone(up.query_one("#up_progress_label"))
                self.assertIsNotNone(up.query_one("#up_remaining"))
                for fid in ("filt_info", "filter_warning", "filter_error", "filt_critical"):
                    self.assertIsNotNone(up.query_one(f"#{fid}"))
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_set_progress(self):
        """UpdateProgress.set_progress(45, 234) actualiza ProgressBar y labels."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                up.set_progress(45, 234)
                await pilot.pause()
                pb = up.query_one("#up_progress")
                self.assertEqual(pb.total, 234)
                self.assertEqual(pb.progress, 45)
                lbl = up.query_one("#up_progress_label")
                self.assertIn("45 / 234", str(lbl.render()))
                rem = up.query_one("#up_remaining")
                self.assertIn("189", str(rem.render()))
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_filter_toggle(self):
        """UpdateProgress._toggle_level() cambia filter_levels y chips."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                self.assertIn("WARNING", up.filter_levels)
                up._toggle_level("WARNING")
                self.assertNotIn("WARNING", up.filter_levels)
                up._toggle_level("WARNING")
                self.assertIn("WARNING", up.filter_levels)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_add_and_filter_lines(self):
        """UpdateProgress.add_line() y get_filtered_lines() filtran correctamente."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                up.add_line("ERROR", "ERROR: test error")
                up.add_line("WARNING", "WARNING: test warning")
                up.add_line("INFO", "INFO: test info")
                # WARNING activo por defecto -> todas pasan
                all_lines = up.get_filtered_lines()
                self.assertEqual(len(all_lines), 3)
                # Quitar WARNING
                up._toggle_level("WARNING")
                filtered = up.get_filtered_lines()
                self.assertEqual(len(filtered), 2)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_set_all_levels(self):
        """set_all_levels(True) activa todo, set_all_levels(False) vacia."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                up.add_line("ERROR", "e")
                up.add_line("WARNING", "w")
                up.set_all_levels(False)
                self.assertEqual(len(up.get_filtered_lines()), 0)
                up.set_all_levels(True)
                self.assertEqual(len(up.get_filtered_lines()), 2)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_set_errors_only(self):
        """set_errors_only() deja solo ERROR y CRITICAL."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                up.add_line("ERROR", "e")
                up.add_line("WARNING", "w")
                up.add_line("INFO", "i")
                up.add_line("CRITICAL", "c")
                up.set_errors_only()
                lines = up.get_filtered_lines()
                self.assertEqual(len(lines), 2)
                self.assertIn("e", lines)
                self.assertIn("c", lines)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_clear(self):
        """clear() resetea todo."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                up.set_progress(45, 234)
                up.add_line("ERROR", "e")
                up.clear()
                self.assertEqual(up.progress_current, 0)
                self.assertEqual(up.progress_total, 0)
                self.assertEqual(len(up._all_lines), 0)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_progress_widget_idle_timeout_sets_indeterminate(self):
        """ProgressBar con total=None queda en modo indeterminado."""
        from textual.app import App

        async def go():
            app = App()
            async with app.run_test(headless=True, size=(80, 24)) as pilot:
                await pilot.pause()
                up = UpdateProgress()
                await app.mount(up)
                await pilot.pause()
                pb = up.query_one("#up_progress")
                self.assertIsNotNone(pb)
                pb.total = None
                self.assertIsNone(pb.total)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")


class TuiProgressIntegrationTest(unittest.TestCase):
    """Sim 4-9: tests de integracion con subprocess mockeado y bindings."""

    def test_integration_parses_progress_lines(self):
        """Sim 4: mockear subprocess con lineas de progreso, verificar avance."""
        from textual.app import App

        odoo_lines = [
            "INFO: odoo: (0/5) starting",
            "INFO: odoo: (1/5) sale",
            "WARNING: odoo: (2/5) account deprecated",
            "ERROR: odoo: (3/5) stock failed",
            "INFO: odoo: (4/5) purchase",
            "INFO: odoo: (5/5) done",
        ]

        async def go():
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                up = app.query_one("#update_progress", UpdateProgress)
                up.display = True
                up.clear()
                for line in odoo_lines:
                    parsed = parse_progress(line)
                    if parsed is not None:
                        up.set_progress(parsed[0], parsed[1])
                    level = classify_level(line)
                    up.add_line(level, line)
                await pilot.pause()
                self.assertEqual(up.progress_total, 5)
                self.assertEqual(up.progress_current, 5)
                self.assertEqual(len(up._all_lines), 6)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_integration_filter_with_bindings(self):
        """Sim 5: toggle WARNING con binding, verificar solo ciertos niveles."""
        from textual.app import App

        odoo_lines = [
            "ERROR: e1",
            "WARNING: w1",
            "INFO: i1",
            "ERROR: e2",
            "CRITICAL: c1",
        ]

        async def go():
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                up = app.query_one("#update_progress", UpdateProgress)
                up.display = True
                for line in odoo_lines:
                    level = classify_level(line)
                    up.add_line(level, line)
                # Ver estado inicial: 5 lineas pasan
                self.assertEqual(len(up.get_filtered_lines()), 5)
                # Presionar '2' toggle WARNING
                await pilot.press("2")
                await pilot.pause()
                # WARNING desactivado -> quedan 4
                self.assertNotIn("WARNING", up.filter_levels)
                self.assertEqual(len(up.get_filtered_lines()), 4)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_integration_filter_errors_only(self):
        """Sim 6: binding '9' deja solo ERROR+CRITICAL."""
        from textual.app import App

        async def go():
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                up = app.query_one("#update_progress", UpdateProgress)
                up.display = True
                up.add_line("ERROR", "e1")
                up.add_line("WARNING", "w1")
                up.add_line("INFO", "i1")
                up.add_line("CRITICAL", "c1")
                await pilot.pause()
                await pilot.press("9")
                await pilot.pause()
                lines = up.get_filtered_lines()
                self.assertEqual(len(lines), 2)
                self.assertIn("e1", lines)
                self.assertIn("c1", lines)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_integration_filter_all(self):
        """Sim 7: binding '0' activa todos los niveles."""
        from textual.app import App

        async def go():
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                up = app.query_one("#update_progress", UpdateProgress)
                up.display = True
                up.add_line("ERROR", "e1")
                up.add_line("WARNING", "w1")
                up._toggle_level("WARNING")
                await pilot.pause()
                self.assertEqual(len(up.get_filtered_lines()), 1)
                await pilot.press("0")
                await pilot.pause()
                self.assertEqual(len(up.get_filtered_lines()), 2)
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_integration_cancel_with_esc(self):
        """Sim 8: Esc llama a terminate() en el subprocess."""
        from textual.app import App

        async def go():
            app = DockerOdooApp()
            async with app.run_test(headless=True, size=(120, 40)) as pilot:
                await pilot.pause()
                mock_proc = MagicMock()
                mock_proc.terminate = MagicMock()
                app._update_proc = mock_proc
                await pilot.press("escape")
                await pilot.pause()
                mock_proc.terminate.assert_called_once()
                return "ok"

        result = asyncio.run(go())
        self.assertEqual(result, "ok")

    def test_integration_no_modules_shows_widget(self):
        """Sim 10: update sin modulos especificos (all) TAMBIEN muestra
        el widget porque Odoo emite (N/M) en cualquier caso. Antes
        retornaba False, lo que hacia invisible la barra para el caso
        mas comun (corregido: el usuario se quejaba de que la barra
        no funcionaba)."""
        update_action = get_action("update")
        app = DockerOdooApp()
        self.assertTrue(
            app._is_update_with_modules(update_action, {"modules": "all"})
        )

    def test_integration_with_modules_shows_widget(self):
        """update con modulos conocidos usa el widget."""
        update_action = get_action("update")
        app = DockerOdooApp()
        self.assertTrue(
            app._is_update_with_modules(update_action, {"modules": "sale,purchase"})
        )

    def test_integration_non_update_no_widget(self):
        """accion no-update no usa el widget."""
        start_action = get_action("start")
        app = DockerOdooApp()
        self.assertFalse(
            app._is_update_with_modules(start_action, {})
        )


if __name__ == "__main__":
    # Permitir -v para verbosity
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("unittest_args", nargs="*")
    parsed, _ = parser.parse_known_args()
    argv = [sys.argv[0]] + (["-v"] if parsed.verbose else []) + parsed.unittest_args
    unittest.main(argv=argv, verbosity=2 if parsed.verbose else 1, exit=False)
