"""Tests for the interactive prompts that don't need a real TTY.

Run with::

    python3 -m unittest tests.test_prompts -v
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)

from odoo_cli.core.prompts import prompt_for_tag  # noqa: E402


class FakeRunner:
    """Minimal Runner stub: pre-loaded text answers, recorded messages."""

    def __init__(self, text_answers: list[str]) -> None:
        self.messages: list[tuple[str, str]] = []
        self._text_q = list(text_answers)

    def info(self, msg: str) -> None:
        self.messages.append(("info", msg))

    def prompt_text(self, prompt: str, default: str = "") -> str:
        return self._text_q.pop(0) if self._text_q else default


class PromptForTagTest(unittest.TestCase):
    """A filter with no matches must re-ask, never kill the process."""

    def _run(self, text_answers, tags=("17.0.1.0.0", "17.0.2.0.0-beta.1")):
        runner = FakeRunner(text_answers)
        with patch("subprocess.run") as run_mock, patch(
            "odoo_cli.core.prompts.prompt_selection",
            return_value=tags[0] if tags else None,
        ):
            run_mock.return_value.stdout = "\n".join(tags) + "\n"
            result = prompt_for_tag(runner, "/fake/submodule/path")
        return runner, result

    def test_no_match_reasks_instead_of_exiting(self):
        runner, result = self._run(["does-not-exist", ""])
        self.assertEqual(result, "17.0.1.0.0")
        error_texts = [m[1] for m in runner.messages]
        self.assertTrue(
            any("Ningún tag coincide" in t for t in error_texts),
            f"Se esperaba el aviso de 'no coincide'. Mensajes: {error_texts}",
        )

    def test_matching_filter_on_first_try_does_not_reask(self):
        runner, result = self._run(["beta"])
        self.assertEqual(result, "17.0.1.0.0")
        self.assertFalse(
            any("Ningún tag coincide" in m[1] for m in runner.messages)
        )

    def test_repeated_no_match_keeps_reasking(self):
        runner, result = self._run(["nope", "still-nope", "beta"])
        self.assertEqual(result, "17.0.1.0.0")
        no_match_msgs = [m for m in runner.messages if "Ningún tag coincide" in m[1]]
        self.assertEqual(len(no_match_msgs), 2)


class FitMenuItemTest(unittest.TestCase):
    """Menu rows must never wrap: the redraw counts one line per row."""

    def test_single_column_is_not_padded(self):
        from odoo_cli.core.prompts import _fit_menu_item

        self.assertEqual(_fit_menu_item("❯  1. Producción", 1, 90, 60), "❯  1. Producción")

    def test_long_item_is_clipped_to_the_terminal(self):
        from odoo_cli.core.prompts import _fit_menu_item

        fitted = _fit_menu_item("x" * 200, 1, 210, 60)
        self.assertEqual(len(fitted), 59)
        self.assertTrue(fitted.endswith("…"))

    def test_grid_columns_are_padded_within_the_terminal(self):
        from odoo_cli.core.prompts import _fit_menu_item

        fitted = _fit_menu_item("  1. acme", 3, 20, 80)
        self.assertEqual(len(fitted), 20)


if __name__ == "__main__":
    unittest.main()
