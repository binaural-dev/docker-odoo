"""VS Code debugging: ``./odoo vscode <instance>``.

Prepares the host so VS Code can attach to an instance started with
``"debug": true`` in ``instances.json`` (Odoo running under debugpy):

  * Copies the Odoo core installed in the container
    (``/usr/lib/python3/dist-packages/odoo``, from the nightly .deb) to
    ``.odoo-src/<instance>/odoo`` so it can be read and breakpointed.
    It is copied per instance because each instance keeps its own
    ``/usr/lib`` volume, so two instances on the same version can still
    hold different nightly builds.
  * Writes (or updates) an "attach" entry for the instance in
    ``.vscode/launch.json`` mapping both ``src/`` and the copied core to
    their paths inside the container.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from odoo_cli.core.actions.lifecycle import COMPOSE_FILE
from odoo_cli.core.actions.validate import DEFAULT_DEBUG_PORT

ODOO_CORE_REMOTE = "/usr/lib/python3/dist-packages/odoo"
SOURCES_REMOTE = "/home/odoo/src"
CORE_SRC_DIR = ".odoo-src"


def launch_configuration(instance: str, port: int) -> dict:
    """The VS Code "attach" configuration for one instance."""
    return {
        "name": f"Odoo: {instance}",
        "type": "debugpy",
        "request": "attach",
        "connect": {"host": "localhost", "port": port},
        "pathMappings": [
            {
                "localRoot": "${workspaceFolder}/src",
                "remoteRoot": SOURCES_REMOTE,
            },
            {
                "localRoot": f"${{workspaceFolder}}/{CORE_SRC_DIR}/{instance}/odoo",
                "remoteRoot": ODOO_CORE_REMOTE,
            },
        ],
        # Needed to step into / stop in the Odoo core, not only in src/.
        "justMyCode": False,
    }


def _write_launch_json(runner: "Runner", base_path: str, configuration: dict) -> None:
    """Add or replace ``configuration`` (matched by name) in launch.json.

    launch.json may contain comments (JSONC); if it doesn't parse as
    plain JSON it is left untouched and the entry is printed instead,
    so hand-written content is never lost.
    """
    vscode_dir = os.path.join(base_path, ".vscode")
    launch_path = os.path.join(vscode_dir, "launch.json")

    data = {"version": "0.2.0", "configurations": []}
    if os.path.exists(launch_path):
        with open(launch_path) as f:
            raw = f.read()
        if raw.strip():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                runner.warn(
                    f"\n⚠️  {launch_path} no es JSON plano (¿tiene comentarios?). "
                    "No lo modifico; agrega esta configuración a mano en "
                    "'configurations':\n"
                )
                runner.info(json.dumps(configuration, indent=4))
                return

    configurations = [
        c for c in data.get("configurations", [])
        if c.get("name") != configuration["name"]
    ]
    configurations.append(configuration)
    data["configurations"] = configurations
    data.setdefault("version", "0.2.0")

    os.makedirs(vscode_dir, exist_ok=True)
    with open(launch_path, "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")
    runner.info(f"  ✓ {launch_path}: configuración '{configuration['name']}'")


def setup_vscode(runner: "Runner", config: dict, base_path: str, instance: str) -> int:
    """Copy the Odoo core to the host and write the VS Code attach config."""
    if instance not in config["instances"]:
        runner.error(f"\n❌ La instancia '{instance}' no existe en instances.json.")
        return 1
    inst_conf = config["instances"][instance]
    port = inst_conf.get("debug_port", DEFAULT_DEBUG_PORT)
    service = f"odoo-{instance}"

    runner.info(f"\n=== 🐞 PREPARANDO VS CODE PARA: {instance.upper()} ===\n")

    if not inst_conf.get("debug"):
        runner.warn(
            f"⚠️  La instancia '{instance}' no tiene \"debug\": true en "
            "instances.json. Actívalo y corre './odoo build' y "
            f"'./odoo restart {instance}' para poder conectar el depurador.\n"
        )

    # Replace (not merge) the previous copy so files removed upstream
    # don't linger and get stale breakpoints.
    core_parent = os.path.join(base_path, CORE_SRC_DIR, instance)
    core_dest = os.path.join(core_parent, "odoo")
    if os.path.isdir(core_dest):
        shutil.rmtree(core_dest)
    os.makedirs(core_parent, exist_ok=True)

    runner.info(f"Copiando el código base de Odoo a {CORE_SRC_DIR}/{instance}/odoo ...")
    rc = runner.run_streamed(
        [
            "docker", "compose", "-f", COMPOSE_FILE, "cp",
            f"{service}:{ODOO_CORE_REMOTE}", core_dest,
        ],
        cwd=base_path,
    )
    if rc != 0:
        runner.error(
            f"\n❌ No se pudo copiar el código base desde '{service}'. "
            f"¿Existe el contenedor? Prueba con: ./odoo start {instance}"
        )
        return rc

    _write_launch_json(runner, base_path, launch_configuration(instance, port))

    runner.info(
        "\nListo. En VS Code: abre esta carpeta, ve a 'Ejecutar y depurar' "
        f"y lanza 'Odoo: {instance}'.\n"
    )
    return 0
