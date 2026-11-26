"""``./odoo config``: set an instance's type (production/test) and profile.

Deliberately small: an instance is either production or test, and runs on
one of the ``odoo_configs`` profiles defined in instances.json (workers,
memory limits and the rest live there). ``--db-filter`` optionally sets
the instance's ``db_filter`` in the same run. Anything finer is edited in
the JSON by hand. The Postgres side (postgresql.*.conf of a service) is
``./odoo db-config``, see :mod:`odoo_cli.core.actions.db_config`.

Production (``production: true``) blocks ``./odoo remove``, forbids
``dev_mode`` and makes nginx refuse ``/web/database/``; it also turns
``list_db`` off for the instance, since with it on the database manager
(backup, drop, restore) is one master password away from anyone who can
reach the site. Test turns ``list_db`` back on.

Only the instance entry is touched (root keys, ``odoo_config`` and its own
``overwrite_odoo_config``), never the shared profiles. The result goes
through the same validation as ``load_config`` before anything is written,
and compose/nginx are regenerated to match.
"""

from __future__ import annotations

import copy
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


MODES = {
    "prod": {
        "label": "Producción",
        # Told once, after applying: menus only show the label.
        "effect": (
            "no se puede borrar con ./odoo remove y el administrador de bases "
            "(/web/database) queda cerrado"
        ),
        "production": True,
        "list_db": False,
    },
    "test": {
        "label": "Pruebas",
        "effect": "se puede borrar y el administrador de bases queda abierto",
        "production": False,
        "list_db": True,
    },
}
# What the CLI accepts as the mode argument.
MODE_ALIASES = {
    "prod": "prod",
    "produccion": "prod",
    "test": "test",
    "pruebas": "test",
}


def _current_mode(inst_conf: dict) -> str:
    from generators.config_loader import is_production_instance

    return "prod" if is_production_instance(inst_conf) else "test"


def _ask_mode(runner: "Runner", instance: str, current: str) -> str | None:
    options = [(mode["label"], key) for key, mode in MODES.items()]
    return runner.select_one(
        f"¿{instance} es de producción o de pruebas? (hoy: {MODES[current]['label']})",
        options,
    )


def _ask_profile(
    runner: "Runner", full_config: dict, instance: str, current: str
) -> str | None:
    profiles = full_config["odoo_configs"]
    if len(profiles) == 1:
        return current
    return runner.select_one(
        f"Perfil de configuración de {instance} (hoy: {current})",
        [(name, name) for name in profiles],
    )


def _validate(full_config: dict) -> None:
    """Same checks ``load_config`` runs, on the enabled subset."""
    from generators.config_loader import _validate_config, is_instance_enabled

    enabled = dict(full_config)
    enabled["instances"] = {
        name: inst
        for name, inst in full_config["instances"].items()
        if is_instance_enabled(inst)
    }
    _validate_config(enabled, require_instances=False)


# ``db_filter`` value meaning "not passed: keep the current one, don't ask".
KEEP = object()


def configure_instance(
    runner: "Runner",
    base_path: str,
    instance: str,
    mode: str | None = None,
    profile: str | None = None,
    db_filter=KEEP,
) -> None:
    """Set ``instance`` to ``mode`` (prod/test) on ``profile``, asking for
    whatever wasn't given.

    ``db_filter``:
        * ``KEEP`` (default)      → keep whatever is already set, don't ask.
        * ``None``                → ask interactively.
        * ``""``                  → remove the db_filter from overwrite_odoo_config.
        * any string              → set that exact regex.

    Validates, saves once and regenerates.
    """
    from generators.config_loader import load_full_config
    from odoo_cli.core.actions.instance_state import (
        _regenerate_configs,
        _write_instances_json,
    )
    from odoo_cli.core.actions.lifecycle import COMPOSE_FILE
    from odoo_cli.core.actions.postgres import _confirm_or_skip

    full_config = load_full_config(base_path)
    if instance not in full_config["instances"]:
        runner.error(f"Error: instancia '{instance}' no existe en instances.json.")
        sys.exit(1)
    if profile is not None and profile not in full_config["odoo_configs"]:
        runner.error(
            f"Error: perfil '{profile}' no existe. Disponibles: "
            f"{', '.join(full_config['odoo_configs'])}"
        )
        sys.exit(1)

    inst_conf = full_config["instances"][instance]
    current_mode = _current_mode(inst_conf)
    current_profile = inst_conf["odoo_config"]
    current_filter = inst_conf.get("overwrite_odoo_config", {}).get("db_filter", "")

    if mode is None:
        mode = _ask_mode(runner, instance, current_mode)
    else:
        mode = MODE_ALIASES[mode]
    if profile is None and mode is not None:
        profile = _ask_profile(runner, full_config, instance, current_profile)
    if mode is None or profile is None:
        runner.info("Cancelado.")
        return

    # --- db_filter resolution ---
    if db_filter is KEEP:
        resolved_filter = KEEP
    elif db_filter is None:
        # asked to prompt interactively
        resolved_filter = _ask_db_filter(runner, instance, current_filter)
    else:
        resolved_filter = db_filter

    preset = MODES[mode]
    overwrite = inst_conf.get("overwrite_odoo_config", {})

    filter_unchanged = resolved_filter is KEEP or resolved_filter == current_filter
    if (
        mode == current_mode
        and profile == current_profile
        and overwrite.get("list_db") is preset["list_db"]
        and filter_unchanged
    ):
        runner.info(
            f"\nSin cambios: {instance} ya es de {preset['label']} con el perfil {profile}.\n"
        )
        return

    if current_mode == "prod" and mode == "test" and not _confirm_or_skip(
        runner,
        f"{instance} deja de ser de producción: se va a poder borrar y el "
        f"administrador de bases queda abierto. ¿Continuar?",
    ):
        runner.info("Cancelado.")
        return

    updated = copy.deepcopy(full_config)
    target = updated["instances"][instance]
    target["production"] = preset["production"]
    target["odoo_config"] = profile
    ow = target.setdefault("overwrite_odoo_config", {})
    ow["list_db"] = preset["list_db"]

    if resolved_filter is not KEEP:
        if resolved_filter:
            ow["db_filter"] = resolved_filter
        else:
            # empty string → remove the key
            ow.pop("db_filter", None)

    try:
        _validate(updated)
    except ValueError as exc:
        runner.error(f"\n❌ No se guardó nada, la configuración quedaría inválida:\n{exc}")
        sys.exit(1)

    success, error_message = _write_instances_json(base_path, updated)
    if not success:
        runner.error(f"\n❌ No se pudo guardar instances.json: {error_message}")
        sys.exit(1)

    runner.info(
        f"\n✅ {instance} ahora es de {preset['label']} (perfil {profile}): "
        f"{preset['effect']}."
    )
    if resolved_filter is not KEEP:
        shown = resolved_filter or "(sin filtro)"
        runner.info(f"   db_filter → {shown}")
    runner.info("→ Regenerando docker-compose.generated.yml y nginx...")
    _regenerate_configs(updated)

    services = f"odoo-{instance}"
    if mode != current_mode:
        services += " nginx"
    runner.info(
        "\nPara aplicarlo, recreá los contenedores: docker compose -f "
        f"{COMPOSE_FILE} up -d --no-deps {services}\n"
    )


def _ask_db_filter(runner: "Runner", instance: str, current: str) -> str:
    """Ask for a db_filter regex. Enter keeps ``current``; ``-`` removes it."""
    runner.info(
        f"\nFiltro de base de datos de {instance} (hoy: {current or 'ninguno'}).\n"
        f"  Ej.: ^{instance}   ·   Enter = dejarlo como está   ·   - = quitarlo"
    )
    value = runner.prompt_text("db_filter").strip()
    if value == "":
        return current
    if value == "-":
        return ""
    return value


__all__ = ["KEEP", "MODES", "MODE_ALIASES", "configure_instance"]
