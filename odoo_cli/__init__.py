"""Package marker for the extracted core logic of ``./odoo``.

Holds the ``Runner`` abstraction and the action modules that operate on it.
The thin dispatcher in :mod:`odoo_cli.core.dispatch` wires argparse to the
actions so both ``./odoo`` and ``./odoo tui`` can share the same code.
"""
