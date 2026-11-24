"""``./odoo config``: set an instance's type (production/test) and profile.

Deliberately small: an instance is either production or test, and runs on
one of the ``odoo_configs`` profiles defined in instances.json (workers,
memory limits and the rest live there). Anything finer is edited in the
JSON by hand.

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
        "summary": "bloquea ./odoo remove, sin dev_mode, sin administrador de bases",
        "production": True,
        "list_db": False,
    },
    "test": {
        "label": "Pruebas",
        "summary": "administrador de bases habilitado, se puede borrar",
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


def _profile_summary(profile: dict) -> str:
    workers = profile.get("workers", "?")
    return f"workers {workers}"


def _show(runner: "Runner", full_config: dict, instance: str) -> None:
    inst_conf = full_config["instances"][instance]
    profile = inst_conf["odoo_config"]
    runner.info(f"\n=== ⚙️  {instance} ===")
    runner.info(f"  Tipo:   {MODES[_current_mode(inst_conf)]['label']}")
    runner.info(
        f"  Perfil: {profile} "
        f"({_profile_summary(full_config['odoo_configs'][profile])})\n"
    )


def _ask_mode(runner: "Runner", current: str) -> str | None:
    options = []
    for key, mode in MODES.items():
        mark = " (actual)" if key == current else ""
        options.append((f"{mode['label']}{mark} — {mode['summary']}", key))
    return runner.select_one("Tipo de instancia", options)


def _ask_profile(runner: "Runner", full_config: dict, current: str) -> str | None:
    profiles = full_config["odoo_configs"]
    if len(profiles) == 1:
        return current
    ordered = [current] + [name for name in profiles if name != current]
    options = [
        (
            f"{name}{' (actual)' if name == current else ''} — "
            f"{_profile_summary(profiles[name])}",
            name,
        )
        for name in ordered
    ]
    return runner.select_one("Perfil de configuración", options)


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


def configure_instance(
    runner: "Runner",
    base_path: str,
    instance: str,
    mode: str | None = None,
    profile: str | None = None,
) -> None:
    """Set ``instance`` to ``mode`` (prod/test) on ``profile``, asking for
    whatever wasn't given. Validates, saves once and regenerates."""
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
    _show(runner, full_config, instance)

    if mode is None:
        mode = _ask_mode(runner, current_mode)
    else:
        mode = MODE_ALIASES[mode]
    if profile is None and mode is not None:
        profile = _ask_profile(runner, full_config, current_profile)
    if mode is None or profile is None:
        runner.info("Cancelado.")
        return

    preset = MODES[mode]
    overwrite = inst_conf.get("overwrite_odoo_config", {})
    if (
        mode == current_mode
        and profile == current_profile
        and overwrite.get("list_db") is preset["list_db"]
    ):
        runner.info("Sin cambios.\n")
        return

    if current_mode == "prod" and mode == "test" and not _confirm_or_skip(
        runner,
        f"'{instance}' deja de ser de producción: se va a poder borrar y "
        f"vuelve el administrador de bases. ¿Continuar?",
    ):
        runner.info("Cancelado.")
        return

    updated = copy.deepcopy(full_config)
    target = updated["instances"][instance]
    target["production"] = preset["production"]
    target["odoo_config"] = profile
    target.setdefault("overwrite_odoo_config", {})["list_db"] = preset["list_db"]
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
        f"✅ '{instance}': {preset['label']} ({preset['summary']}), perfil {profile}."
    )
    runner.info("→ Regenerando docker-compose.generated.yml y nginx...")
    _regenerate_configs(updated)

    services = f"odoo-{instance}"
    if mode != current_mode:
        services += " nginx"
    runner.info(
        "\nPara aplicarlo, recreá los contenedores: docker compose -f "
        f"{COMPOSE_FILE} up -d --no-deps {services}\n"
    )


__all__ = ["MODES", "MODE_ALIASES", "configure_instance"]
