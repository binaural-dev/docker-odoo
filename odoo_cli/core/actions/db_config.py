"""``./odoo db-config``: pick the postgresql.*.conf of a database service.

The profiles are whatever ``postgresql*.conf`` files exist in
``.resources/dbconfigs`` — read from disk, not hardcoded, so a server with
its own tuned file (e.g. ``postgresql.conf``) can keep selecting it. Only
managed services (``create_container`` true) are offered: for an external
Postgres the ``config`` key does nothing.
"""

from __future__ import annotations

import copy
import glob
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


DB_CONFIGS_DIR = os.path.join(".resources", "dbconfigs")
# Shipped profiles first, smallest to largest; anything else after, by name.
_SIZE_ORDER = ["small", "medium", "large", "xlarge"]


def available_db_configs(base_path: str) -> list[str]:
    """``postgresql*.conf`` file names in ``.resources/dbconfigs``."""
    pattern = os.path.join(base_path, DB_CONFIGS_DIR, "postgresql*.conf")
    names = [os.path.basename(path) for path in glob.glob(pattern)]

    def order(name: str):
        size = name[len("postgresql."):-len(".conf")]
        rank = _SIZE_ORDER.index(size) if size in _SIZE_ORDER else len(_SIZE_ORDER)
        return rank, name

    return sorted(names, key=order)


def configure_db(
    runner: "Runner",
    base_path: str,
    db_service: str | None = None,
    db_config: str | None = None,
) -> None:
    """Change the ``config`` (postgresql.*.conf) of a database service.

    ``db_service`` is a key in ``instances.json.databases`` (e.g. ``v19``);
    ``db_config`` a file name from :func:`available_db_configs`. Both are
    asked interactively when omitted.
    """
    from generators.config_loader import load_full_config
    from odoo_cli.core.actions.instance_state import (
        _regenerate_configs,
        _write_instances_json,
    )
    from odoo_cli.core.actions.lifecycle import COMPOSE_FILE

    full_config = load_full_config(base_path)
    managed = {
        name: conf
        for name, conf in full_config.get("databases", {}).items()
        if conf.get("create_container", True)
    }
    if not managed:
        runner.error(
            "No hay servicios de Postgres gestionados por docker-odoo en "
            "instances.json (los externos no usan 'config')."
        )
        sys.exit(1)

    if db_service is None:
        if len(managed) == 1:
            db_service = next(iter(managed))
            runner.info(f"\nServicio de base de datos: {db_service}")
        else:
            db_service = runner.select_one(
                "Selecciona servicio de base de datos",
                [(name, name) for name in managed],
            )
        if db_service is None:
            runner.info("Cancelado.")
            return

    if db_service not in managed:
        external = db_service in full_config.get("databases", {})
        reason = (
            "es externo (create_container: false): su 'config' no se aplica"
            if external else "no existe"
        )
        runner.error(
            f"Error: el servicio '{db_service}' {reason}. "
            f"Disponibles: {', '.join(managed)}"
        )
        sys.exit(1)

    available = available_db_configs(base_path)
    current_config = managed[db_service].get("config", "(sin definir)")

    if db_config is None:
        db_config = runner.select_one(
            f"Config de Postgres para '{db_service}' (hoy: {current_config})",
            [(name, name) for name in available],
        )
        if db_config is None:
            runner.info("Cancelado.")
            return

    if db_config not in available:
        runner.error(
            f"Error: '{db_config}' no existe en {DB_CONFIGS_DIR}. "
            f"Opciones: {', '.join(available)}"
        )
        sys.exit(1)

    if db_config == current_config:
        runner.info(f"\nSin cambios: '{db_service}' ya usa {current_config}.\n")
        return

    updated = copy.deepcopy(full_config)
    updated["databases"][db_service]["config"] = db_config

    success, error_message = _write_instances_json(base_path, updated)
    if not success:
        runner.error(f"\n❌ No se pudo guardar instances.json: {error_message}")
        sys.exit(1)

    runner.info(f"\n✅ '{db_service}' ahora usa {db_config}.")
    runner.info("→ Regenerando docker-compose.generated.yml y nginx...")
    _regenerate_configs(updated)

    runner.info(
        f"\nPara aplicarlo, recreá el contenedor de base de datos:\n"
        f"  docker compose -f {COMPOSE_FILE} up -d --force-recreate db-{db_service}\n"
        f"\n⚠️  Esto reinicia Postgres. Los contenedores Odoo que dependen de\n"
        f"   '{db_service}' se reconectan solos, pero hay unos segundos de\n"
        f"   indisponibilidad. Verificá con: docker compose -f {COMPOSE_FILE} ps\n"
    )


__all__ = ["available_db_configs", "configure_db"]
