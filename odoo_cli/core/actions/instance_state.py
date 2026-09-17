"""Enable/disable actions: toggle the ``enabled`` flag in instances.json.

This is the scriptable CLI counterpart to the TUI's Space keybinding
(``tui/keybindings.py:action_toggle_instance``): same flag, same file,
same "only enabled instances reach docker-compose.generated.yml"
contract enforced by ``generators.config_loader.load_config``. Kept
independent of the ``tui`` package (no import of it) so the plain CLI
path doesn't pull in Textual just to flip a boolean.

Unlike ``build_odoo``, this never runs ``docker compose build`` — it
only regenerates the compose/nginx files so they match the new state.
Building images and starting/stopping containers stays the caller's
job (see the hint printed at the end).
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


def _write_instances_json(base_path: str, raw_config: dict) -> tuple[bool, str]:
    """Persist ``raw_config`` to ``base_path/instances.json``.

    Same shape as ``instances.json`` after any TUI save: pretty-printed,
    no comments (the ``//`` comments the file may have shipped with are
    lost on the first write — same trade-off the TUI already makes).
    """
    import os

    path = os.path.join(base_path, "instances.json")
    try:
        with open(path, "w") as f:
            json.dump(raw_config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _regenerate_configs(full_config: dict) -> None:
    """Regenerate Dockerfiles/compose/nginx from the enabled subset.

    Mirrors the first three steps of ``build_odoo`` (no image build).
    """
    from generators.dockerfile_generator import generate_dockerfiles
    from generators.compose_generator import generate_compose
    from generators.nginx_generator import generate_nginx_config
    from generators.config_loader import get_unique_odoo_versions, is_instance_enabled

    filtered = dict(full_config)
    filtered["instances"] = {
        name: inst
        for name, inst in full_config.get("instances", {}).items()
        if is_instance_enabled(inst)
    }

    base_path = "."
    unique_versions = get_unique_odoo_versions(filtered)
    dockerfile_map = generate_dockerfiles(base_path, unique_versions)
    generate_compose(base_path, filtered, dockerfile_map)
    generate_nginx_config(base_path, filtered)


def set_instances_enabled(
    runner: "Runner", base_path: str, instances: list[str], enabled: bool
) -> None:
    """Flip ``enabled`` for one or more instances, persist once, regenerate once.

    All-or-nothing on unknown names: if any requested instance doesn't
    exist in instances.json, nothing is written — a typo in a 5-instance
    batch must not silently apply to the other 4.
    """
    from generators.config_loader import load_full_config, is_instance_enabled

    full_config = load_full_config(base_path)
    all_instances = full_config.get("instances", {})

    unknown = [name for name in instances if name not in all_instances]
    if unknown:
        runner.error(f"\n❌ Instancia(s) desconocida(s): {', '.join(unknown)}")
        sys.exit(1)

    estado = "habilitada" if enabled else "deshabilitada"
    changed = [
        name for name in instances
        if is_instance_enabled(all_instances[name]) != enabled
    ]
    already = [name for name in instances if name not in changed]

    if already:
        plural = "n" if len(already) > 1 else ""
        runner.info(f"\nℹ Ya está{plural} {estado}: {', '.join(already)}")

    if not changed:
        runner.info("Nada que hacer.\n")
        return

    for name in changed:
        all_instances[name]["enabled"] = enabled

    success, error_message = _write_instances_json(base_path, full_config)
    if not success:
        runner.error(f"\n❌ No se pudo guardar instances.json: {error_message}")
        sys.exit(1)

    runner.info(f"\n✅ {estado.capitalize()}(s): {', '.join(changed)}\n")

    runner.info("→ Regenerando docker-compose.generated.yml y nginx...")
    _regenerate_configs(full_config)
    runner.info("✅ Configs regenerados.\n")

    if enabled:
        if len(changed) == 1:
            runner.info(f"Para levantarla: ./odoo build && ./odoo start {changed[0]}\n")
        else:
            runner.info(
                "Para levantarlas: ./odoo build && ./odoo start "
                f"{changed[0]} (repetí ./odoo start por cada una: "
                f"{', '.join(changed)})\n"
            )
    else:
        runner.info(
            "Nota: si algún contenedor seguía corriendo, esto no lo detiene "
            f"— corré './odoo stop <instancia>' por cada una si hace falta: "
            f"{', '.join(changed)}\n"
        )


__all__ = ["set_instances_enabled"]
