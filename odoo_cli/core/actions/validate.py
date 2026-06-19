"""Validation of ``instances.json``.

The legacy ``./odoo validate-instances`` subcommand and the
``main()`` pre-dispatch check both call into this module. Keeping the
validation logic in one place means the dispatch path is the only
caller, and the rules (no duplicate ports, every instance references
a defined database) are documented next to the code that enforces
them.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


def validate_instances(runner: "Runner", config: dict) -> None:
    """Validate ``instances.json`` for duplicate ports and valid configuration.

    Reports errors through ``runner.error`` and exits with status 1 on
    the first batch of problems. The function does not return on
    failure (``SystemExit``); on success it returns ``None``.
    """
    ports_seen: dict[int, str] = {}
    errors: list[str] = []

    # Check database ports (host-side). Multiple DBs sharing the same host port
    # is the most common multi-instance pitfall: only one can bind it.
    for db_name, db_conf in config.get("databases", {}).items():
        port = db_conf.get("port")
        if not port:
            continue
        if port in ports_seen:
            errors.append(
                f"Puerto duplicado: {port} usado por la base '{db_name}' "
                f"y '{ports_seen[port]}'"
            )
        else:
            ports_seen[port] = f"base de datos '{db_name}'"

    # Check pgadmin port
    if config.get("pgadmin", {}).get("enabled"):
        port = config["pgadmin"].get("port")
        if port:
            if port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {port} usado por 'pgadmin' "
                    f"y '{ports_seen[port]}'"
                )
            else:
                ports_seen[port] = "pgadmin"

    # Check mailhog http_port (web UI exposed on the host)
    if config.get("mailhog", {}).get("enabled"):
        port = config["mailhog"].get("http_port")
        if port:
            if port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {port} usado por 'mailhog' "
                    f"y '{ports_seen[port]}'"
                )
            else:
                ports_seen[port] = "mailhog"

    # Check instances
    for name, inst in config.get("instances", {}).items():
        # Check external_port
        ext_port = inst.get("external_port")
        if ext_port:
            if ext_port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {ext_port} usado por '{name}' "
                    f"y '{ports_seen[ext_port]}'"
                )
            else:
                ports_seen[ext_port] = f"instancia {name} (external_port)"

        # Check longpolling_port
        lp_port = inst.get("longpolling_port")
        if lp_port:
            if lp_port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {lp_port} usado por '{name}' "
                    f"y '{ports_seen[lp_port]}'"
                )
            else:
                ports_seen[lp_port] = f"instancia {name} (longpolling_port)"

        # Check db existence
        db_name = inst.get("database")
        if db_name and db_name not in config.get("databases", {}):
            errors.append(
                f"La instancia '{name}' usa la base de datos '{db_name}' "
                f"que no está definida en 'databases'."
            )

    if errors:
        runner.error("\n=== ❌ ERROR DE VALIDACIÓN EN instances.json ===\n")
        for err in errors:
            runner.error(f"  - {err}")
        runner.error("")
        sys.exit(1)
