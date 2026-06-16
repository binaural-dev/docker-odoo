"""Runner protocol — the user-I/O surface used by every action module.

Why a Protocol (and not an ABC)?
-------------------------------
The actions live in :mod:`odoo_cli.core.actions` and need to call
``runner.info(...)``, ``runner.confirm(...)``, ``runner.run_streamed(...)``,
etc. We want them to be testable with a ``FakeRunner`` that records calls
and stubs subprocess. We also want them to be callable from the real
``CliRunner`` and, eventually, a ``TextualRunner``.

A :class:`typing.Protocol` gives us structural typing: the actions can
type-annotate ``runner: Runner`` and Python's duck typing is enough.
The action modules do not need to import the protocol at runtime to
work; the protocol is for humans and type checkers, not for the
runtime contract.

The future ``TextualRunner`` (out of scope for this batch) will be a
separate class in this package that implements the same protocol but
routes every method to the Textual event loop / widgets. It will be
wired up when the TUI starts using the action modules directly.
"""

from __future__ import annotations

from typing import Callable, Protocol


class Runner(Protocol):
    """User-I/O surface consumed by every action module.

    Implementations are responsible for translating these calls into
    stdout/stdin/subprocess (CLI) or into widget events (Textual).
    Actions should NEVER call ``print``/``input``/``subprocess.run``
    directly — they must go through the runner.
    """

    def info(self, msg: str) -> None:
        """Render an informational line (cyan in the CLI)."""

    def warn(self, msg: str) -> None:
        """Render a warning line (yellow in the CLI)."""

    def error(self, msg: str) -> None:
        """Render an error line (red in the CLI). Errors do not exit."""

    def confirm(self, prompt: str, default: bool = False) -> bool:
        """Ask the user a yes/no question. Returns True/False.

        ``default`` is used when the user just hits Enter.
        """

    def select_one(
        self, title: str, options: list[tuple[str, str]]
    ) -> str | None:
        """Show a single-choice menu. Returns the selected value, or None.

        ``options`` is a list of ``(label, value)`` tuples.
        """

    def select_many(
        self, title: str, options: list[tuple[str, str]]
    ) -> list[str]:
        """Show a multi-choice menu. Returns the list of selected values.

        Empty list means the user selected nothing (allowed in multi
        mode). The caller decides how to interpret that.
        """

    def prompt_text(self, prompt: str, default: str = "") -> str:
        """Ask the user for a free-form text input."""

    def run_streamed(
        self,
        argv: list[str],
        cwd: str,
        on_line: Callable[[str], None] | None = None,
    ) -> int:
        """Run a subprocess and stream stdout line-by-line to ``on_line``.

        Returns the process returncode. Used for non-interactive
        commands whose output the user wants to see (e.g. ``docker
        compose build``).
        """

    def run_interactive(self, argv: list[str], cwd: str) -> int:
        """Run a subprocess attached to the current terminal (no capture).

        Used for commands that take over the TTY themselves (e.g.
        ``docker exec -it ... bash``).
        """
