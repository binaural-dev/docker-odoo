"""Concrete :class:`Runner` implementation backed by print/input/subprocess.

This is the implementation the ``./odoo`` CLI has always used, just
extracted into a class so the action modules can call it without
importing ``subprocess``/``builtins`` directly.

The ANSI color codes match the legacy ``./odoo`` output:
  * cyan  (\\033[1;36m) for info
  * yellow (\\033[1;33m) for warn
  * red   (\\033[1;31m) for error

The simple ``input()`` fallback for ``select_one`` / ``select_many`` is
intentionally minimal: in commit 6 (extract prompts) it will be
replaced by the full ANSI grid menu that lives in
:mod:`odoo_cli.core.prompts`. We do NOT want to drag that menu into
this module — keeping the surface small is what lets the future
``TextualRunner`` override it cleanly.
"""

from __future__ import annotations

import subprocess
from typing import Callable


# ANSI helpers — kept module-local so this file stays the single source
# of truth for the CLI's output colors.
_INFO = "\033[1;36m"   # cyan
_WARN = "\033[1;33m"   # yellow
_ERR = "\033[1;31m"    # red
_RESET = "\033[0m"


class CliRunner:
    """Runner implementation that uses print / input / subprocess.run."""

    # ---- logging ----------------------------------------------------

    def info(self, msg: str) -> None:
        print(f"{_INFO}{msg}{_RESET}")

    def warn(self, msg: str) -> None:
        print(f"{_WARN}{msg}{_RESET}")

    def error(self, msg: str) -> None:
        print(f"{_ERR}{msg}{_RESET}")

    # ---- prompts ----------------------------------------------------

    def confirm(self, prompt: str, default: bool = False) -> bool:
        """Read a y/N answer. Empty input returns ``default``.

        The prompt itself is left untouched (no color) so the user's
        terminal renders it however it wants.
        """
        suffix = "(S/n): " if default else "(s/N): "
        raw = input(prompt + " " + suffix).strip().lower()
        if not raw:
            return default
        return raw == "s"

    def select_one(
        self, title: str, options: list[tuple[str, str]]
    ) -> str | None:
        """Single-choice menu.

        In commit 6 this delegates to
        :func:`odoo_cli.core.prompts.prompt_selection`. Until then we
        fall back to a numbered list + ``input()`` so the runner is
        usable in isolation (and testable with ``unittest.mock``).
        """
        try:
            from odoo_cli.core.prompts import prompt_selection

            return prompt_selection(self, options, title, multi=False)
        except ImportError:
            # prompts module not yet extracted (commits 1-5); use a
            # dumb numbered fallback that is enough to drive tests.
            if not options:
                return None
            print(f"\n{title}:")
            for i, (label, _) in enumerate(options, 1):
                print(f"  {i}. {label}")
            while True:
                raw = input("\nSelección: ").strip()
                if not raw:
                    continue
                try:
                    idx = int(raw)
                except ValueError:
                    print("Por favor ingresa un número válido.")
                    continue
                if 1 <= idx <= len(options):
                    return options[idx - 1][1]
                print("Selección inválida.")

    def select_many(
        self, title: str, options: list[tuple[str, str]]
    ) -> list[str]:
        """Multi-choice menu (Space to toggle, Enter to confirm).

        Same fallback story as :meth:`select_one`.
        """
        try:
            from odoo_cli.core.prompts import prompt_selection

            return prompt_selection(self, options, title, multi=True)
        except ImportError:
            if not options:
                return []
            print(f"\n{title}:")
            for i, (label, _) in enumerate(options, 1):
                print(f"  {i}. {label}")
            print("  (Ingresa números separados por coma, ej: 1,3,4 o 'all')")
            while True:
                raw = input("\nSelección: ").strip().lower()
                if not raw:
                    return []
                if raw == "all":
                    return [val for _, val in options]
                try:
                    indices = [
                        int(x.strip())
                        for x in raw.replace(",", " ").split()
                        if x.strip()
                    ]
                except ValueError:
                    print("Por favor ingresa un valor válido.")
                    continue
                selected = [
                    options[i - 1][1] for i in indices
                    if 1 <= i <= len(options)
                ]
                return selected

    def prompt_text(self, prompt: str, default: str = "") -> str:
        """Read a line of free-form text from stdin."""
        suffix = f" [{default}]: " if default else ": "
        raw = input(prompt + suffix).strip()
        return raw or default

    # ---- subprocess -------------------------------------------------

    def run_streamed(
        self,
        argv: list[str],
        cwd: str,
        on_line: Callable[[str], None] | None = None,
    ) -> int:
        """Run ``argv`` in ``cwd`` and yield each stdout line to ``on_line``.

        We capture stdout so we can stream it line by line (preserving
        the legacy ``./odoo`` behaviour of printing the command before
        running it). ``stderr`` is inherited from the parent process so
        errors from ``docker compose`` and friends are still visible.
        """
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if on_line is not None and result.stdout:
            for line in result.stdout.splitlines():
                on_line(line)
        return result.returncode

    def run_interactive(self, argv: list[str], cwd: str) -> int:
        """Run ``argv`` attached to the parent's terminal (no capture).

        Use this for commands that need a TTY (bash, psql, vim, etc.).
        """
        return subprocess.run(argv, cwd=cwd).returncode
