"""Tests for the ``odoo_cli.core`` Runner abstraction.

Run with::

    python3 -m unittest tests.test_runner -v

These tests intentionally use stdlib ``unittest`` (not pytest) so they
match the style of ``scripts/tui_smoke_test.py`` and have no extra
dependencies.
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from odoo_cli.core import CliRunner


class CliRunnerConfirmTest(unittest.TestCase):
    """``CliRunner.confirm`` accepts the same y/N answers as the legacy CLI."""

    def _ask(self, answer: str, default: bool = False) -> bool:
        runner = CliRunner()
        with patch("builtins.input", return_value=answer), \
             patch("builtins.print"):
            return runner.confirm("¿Continuar?")

    def test_confirm_yes_lower(self):
        self.assertTrue(self._ask("s"))

    def test_confirm_yes_upper(self):
        self.assertTrue(self._ask("S"))

    def test_confirm_no_lower(self):
        self.assertFalse(self._ask("n"))

    def test_confirm_no_upper(self):
        self.assertFalse(self._ask("N"))

    def test_confirm_empty_defaults_to_false(self):
        # No default passed → empty input → False.
        self.assertFalse(self._ask(""))

    def test_confirm_empty_with_default_true(self):
        runner = CliRunner()
        with patch("builtins.input", return_value=""), \
             patch("builtins.print"):
            self.assertTrue(runner.confirm("¿Continuar?", default=True))

    def test_confirm_strips_whitespace(self):
        # "  s  " → still "yes".
        self.assertTrue(self._ask("  s  "))


class CliRunnerSelectOneTest(unittest.TestCase):
    """``CliRunner.select_one`` returns the value at the chosen index."""

    def test_select_one_returns_value(self):
        runner = CliRunner()
        options = [("uno", "1"), ("dos", "2"), ("tres", "3")]
        with patch("builtins.input", return_value="2"), \
             patch("builtins.print"):
            result = runner.select_one("Elegí uno", options)
        self.assertEqual(result, "2")

    def test_select_one_invalid_then_valid(self):
        """A bad answer should be re-prompted; the good answer wins."""
        runner = CliRunner()
        options = [("a", "A"), ("b", "B")]
        # First call returns junk, second returns a real number.
        with patch("builtins.input", side_effect=["foo", "1"]), \
             patch("builtins.print"):
            result = runner.select_one("Elegí", options)
        self.assertEqual(result, "A")

    def test_select_one_empty_options_returns_none(self):
        # With no options, even the real prompts module would return None.
        # We rely on the prompt_selection helper for the legacy fallback.
        runner = CliRunner()
        with patch("builtins.print"):
            # Side effect to skip the loop; we never actually prompt
            # because the options list is empty and prompt_selection
            # short-circuits.
            with patch("builtins.input", return_value="ignored") as m_in:
                result = runner.select_one("vacío", [])
        # prompt_selection (if loaded) returns None; the fallback in
        # CliRunner would loop forever, so we don't reach it. Either
        # way the contract is "no options → None" or "no input needed".
        self.assertIsNone(result)


class CliRunnerSubprocessTest(unittest.TestCase):
    """``CliRunner.run_streamed`` returns the returncode and calls ``on_line``."""

    def test_run_streamed_returns_returncode(self):
        runner = CliRunner()
        fake = unittest.mock.Mock(returncode=0, stdout="hello\nworld\n")
        with patch("odoo_cli.core.cli_runner.subprocess.run", return_value=fake) as m_run:
            code = runner.run_streamed(["echo", "hi"], cwd="/tmp")
        self.assertEqual(code, 0)
        # argv/cwd were forwarded to subprocess.run.
        args, kwargs = m_run.call_args
        self.assertEqual(args[0], ["echo", "hi"])
        self.assertEqual(kwargs["cwd"], "/tmp")
        self.assertTrue(kwargs["text"])
        self.assertTrue(kwargs["capture_output"])

    def test_run_streamed_invokes_on_line(self):
        runner = CliRunner()
        fake = unittest.mock.Mock(returncode=0, stdout="uno\ndos\ntres\n")
        seen: list[str] = []
        with patch("odoo_cli.core.cli_runner.subprocess.run", return_value=fake):
            code = runner.run_streamed(
                ["echo", "x"], cwd="/tmp", on_line=seen.append,
            )
        self.assertEqual(code, 0)
        self.assertEqual(seen, ["uno", "dos", "tres"])

    def test_run_streamed_no_stdout(self):
        """When stdout is empty, on_line is not called (no spurious None)."""
        runner = CliRunner()
        fake = unittest.mock.Mock(returncode=1, stdout="")
        seen: list[str] = []
        with patch("odoo_cli.core.cli_runner.subprocess.run", return_value=fake):
            code = runner.run_streamed(
                ["false"], cwd="/tmp", on_line=seen.append,
            )
        self.assertEqual(code, 1)
        self.assertEqual(seen, [])

    def test_run_interactive_returns_returncode(self):
        runner = CliRunner()
        with patch("odoo_cli.core.cli_runner.subprocess.run") as m_run:
            m_run.return_value = unittest.mock.Mock(returncode=42)
            code = runner.run_interactive(["bash"], cwd="/tmp")
        self.assertEqual(code, 42)
        args, kwargs = m_run.call_args
        self.assertEqual(args[0], ["bash"])
        self.assertEqual(kwargs["cwd"], "/tmp")
        # run_interactive must NOT capture output.
        self.assertNotIn("capture_output", kwargs)


class CliRunnerLoggingTest(unittest.TestCase):
    """info/warn/error go through ``print`` with the right color codes."""

    def test_info_uses_cyan(self):
        runner = CliRunner()
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(" ".join(str(x) for x in a) + "\n")):
            runner.info("hola")
        out = buf.getvalue()
        self.assertIn("hola", out)
        # ANSI cyan = \033[1;36m
        self.assertIn("\033[1;36m", out)
        self.assertIn("\033[0m", out)

    def test_warn_uses_yellow(self):
        runner = CliRunner()
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(" ".join(str(x) for x in a) + "\n")):
            runner.warn("ojo")
        out = buf.getvalue()
        self.assertIn("\033[1;33m", out)

    def test_error_uses_red(self):
        runner = CliRunner()
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(" ".join(str(x) for x in a) + "\n")):
            runner.error("mal")
        out = buf.getvalue()
        self.assertIn("\033[1;31m", out)


if __name__ == "__main__":
    unittest.main()
