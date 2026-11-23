"""Action package: one module per logical group of CLI commands.

Each module exposes functions that take a :class:`odoo_cli.core.Runner`
as their first argument. The runner is the user-I/O surface; actions
must never reach for ``print``/``input``/``subprocess`` directly.

This ``__init__`` is intentionally empty: callers import the action
functions from the specific submodule
(``from odoo_cli.core.actions.validate import validate_instances``).
"""
