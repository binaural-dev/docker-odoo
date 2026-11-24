"""``./odoo config``: show or edit one instance's settings in instances.json.

Edits only touch that instance — root keys (``production``) or its own
``overwrite_odoo_config`` — never the shared ``odoo_configs`` block, which
other instances may inherit from. The result goes through the same
validation as ``load_config`` before anything is written, and the
compose/nginx files are regenerated so they match.

``production: true`` is the "this is a client's live instance" switch: it
blocks ``./odoo remove``, forbids ``dev_mode`` and makes nginx refuse
``/web/database/``. Marking an instance as production also turns
``list_db`` off: with it on, the database manager (backup, drop, restore)
is one master password away from anyone who can reach the site.
"""

from __future__ import annotations

import copy
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


# Settings ``config`` can change, and where they live in the instance entry.
ROOT_KEYS = ("production",)
OVERWRITE_KEYS = (
    "list_db",
    "db_filter",
    "workers",
    "max_cron_threads",
    "limit_memory_soft",
    "limit_memory_hard",
)
_SECRET_KEYS = ("admin_password", "db_password")
_MEMORY_KEYS = ("limit_memory_soft", "limit_memory_hard")
_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMG]?)B?$", re.IGNORECASE)
_SIZE_FACTORS = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


def parse_size(value: str) -> int:
    """``"4G"``/``"512M"``/``"2147483648"`` → bytes (what Odoo expects)."""
    match = _SIZE_RE.match(value.strip())
    if not match:
        raise ValueError(
            f"Tamaño invalido: '{value}' (ejemplos: 4G, 512M, 2147483648)"
        )
    number, unit = match.groups()
    return int(float(number) * _SIZE_FACTORS[unit.upper()])


def _human_size(value) -> str:
    if not isinstance(value, int):
        return str(value)
    gigabyte = _SIZE_FACTORS["G"]
    if value >= gigabyte and value % gigabyte:
        return f"{value / gigabyte:.1f}G ({value} bytes)"
    for unit in ("G", "M", "K"):
        factor = _SIZE_FACTORS[unit]
        if value >= factor and value % factor == 0:
            return f"{value // factor}{unit}"
    return str(value)


def _apply_changes(inst_conf: dict, changes: dict) -> list[str]:
    """Write ``changes`` into ``inst_conf`` and return what was adjusted
    on top of them (for the user to see)."""
    notes = []
    overwrite = inst_conf.setdefault("overwrite_odoo_config", {})
    for key, value in changes.items():
        if key in ROOT_KEYS:
            inst_conf[key] = value
        else:
            overwrite[key] = value

    if changes.get("production") and "list_db" not in changes:
        if overwrite.get("list_db") is not False:
            overwrite["list_db"] = False
            notes.append(
                "list_db: false (produccion no expone el administrador de bases)"
            )
    return notes


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


def show_instance_config(runner: "Runner", full_config: dict, instance: str) -> None:
    """Print the settings ``config`` manages, resolved and with secrets hidden."""
    from generators.config_loader import is_production_instance, resolve_instance_config

    inst_conf = full_config["instances"][instance]
    resolved = resolve_instance_config(inst_conf, full_config)
    overwrite = inst_conf.get("overwrite_odoo_config", {})

    runner.info(f"\n=== ⚙️  {instance} (odoo_config '{inst_conf['odoo_config']}') ===\n")
    runner.info(f"  {'production':<18} {is_production_instance(inst_conf)}")
    for key in OVERWRITE_KEYS:
        if key not in resolved:
            runner.info(f"  {key:<18} (default de Odoo)")
            continue
        value = resolved[key]
        if key in _MEMORY_KEYS:
            value = _human_size(value)
        origin = "instancia" if key in overwrite else "odoo_config"
        runner.info(f"  {key:<18} {value}   [{origin}]")
    for key in _SECRET_KEYS:
        present = bool(resolved.get(key) or inst_conf.get(key))
        runner.info(f"  {key:<18} {'(definida)' if present else '(no definida)'}")
    runner.info(
        "\nPara cambiar algo: ./odoo config "
        f"{instance} --help muestra las opciones.\n"
    )


def configure_instance(
    runner: "Runner", base_path: str, instance: str, changes: dict
) -> None:
    """Apply ``changes`` to ``instance``, validate, save once, regenerate.

    Nothing is written if the result doesn't validate (e.g. ``dev_mode``
    on a production instance).
    """
    from generators.config_loader import load_full_config
    from odoo_cli.core.actions.instance_state import (
        _regenerate_configs,
        _write_instances_json,
    )

    full_config = load_full_config(base_path)
    if instance not in full_config["instances"]:
        runner.error(f"Error: instancia '{instance}' no existe en instances.json.")
        sys.exit(1)

    if not changes:
        show_instance_config(runner, full_config, instance)
        return

    if changes.get("production") and changes.get("list_db"):
        runner.error(
            "Error: una instancia de produccion no puede tener list_db activo "
            "(deja el administrador de bases expuesto). Quitá --list-db."
        )
        sys.exit(1)

    updated = copy.deepcopy(full_config)
    notes = _apply_changes(updated["instances"][instance], changes)
    try:
        _validate(updated)
    except ValueError as exc:
        runner.error(f"\n❌ No se guardó nada, la configuracion quedaria invalida:\n{exc}")
        sys.exit(1)

    success, error_message = _write_instances_json(base_path, updated)
    if not success:
        runner.error(f"\n❌ No se pudo guardar instances.json: {error_message}")
        sys.exit(1)

    runner.info(f"\n✅ '{instance}' actualizada:")
    for key, value in changes.items():
        shown = _human_size(value) if key in _MEMORY_KEYS else value
        runner.info(f"  {key} = {shown}")
    for note in notes:
        runner.info(f"  {note}")

    runner.info("\n→ Regenerando docker-compose.generated.yml y nginx...")
    _regenerate_configs(updated)
    runner.info("✅ Configs regenerados.\n")

    from odoo_cli.core.actions.lifecycle import COMPOSE_FILE

    services = f"odoo-{instance}"
    if "production" in changes:
        services += " nginx"
    runner.info(
        "Para aplicarlo, recreá los contenedores: docker compose -f "
        f"{COMPOSE_FILE} up -d --no-deps {services}\n"
    )


__all__ = ["configure_instance", "parse_size", "show_instance_config"]
