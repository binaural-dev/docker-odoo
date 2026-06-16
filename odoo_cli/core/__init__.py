"""Runner protocol and concrete runner implementations.

A :class:`Runner` is the user-I/O surface that every action in
:mod:`odoo_cli.core.actions` consumes. The intent is to keep the
business logic free of ``print``, ``input`` and ``subprocess`` calls so
that the same action modules can be reused by:

  * :class:`odoo_cli.core.cli_runner.CliRunner` — the existing terminal
    experience, backed by ``print``/``input``/``subprocess.run``.
  * A future :class:`TextualRunner` (NOT in this batch) — the Textual
    TUI reuses the same action modules and routes their I/O through
    Textual widgets instead of stdout/stdin/subprocess.

The contract is intentionally small: a handful of log/confirm/select
methods plus two subprocess wrappers (``run_streamed`` and
``run_interactive``). New I/O needs should be added here and
implemented in BOTH runners; do not let actions reach for ``print`` or
``subprocess`` directly.
"""

from odoo_cli.core.cli_runner import CliRunner
from odoo_cli.core.runner import Runner

__all__ = ["CliRunner", "Runner"]
