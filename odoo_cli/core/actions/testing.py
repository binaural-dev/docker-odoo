"""Test action: runs the standalone ``scripts/odoo-test`` against a
running instance.

``scripts/odoo-test`` is deliberately project-agnostic (see its own
docstring): it doesn't read ``instances.json``, only a Compose *service*
name (``--container``, e.g. ``odoo-<instance>``) and internally shells out
via ``docker compose exec``/``docker compose cp`` — never a raw ``docker
exec``/``docker cp`` against a container name, which is namespaced by the
Compose project and not guaranteed to equal ``odoo-<instance>`` (see
:mod:`odoo_cli.core.actions.access` and ``tests/test_docker_exec_hygiene.py``).
This module just checks the service is actually running before handing off.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

    from odoo_cli.core.runner import Runner

from odoo_cli.core.actions.lifecycle import COMPOSE_FILE


def translate_module_path_tokens(raw_value: str, base_path: str) -> str:
    """Si ``-m``/el posicional de ``test`` trae un path (token con ``/``), lo
    traduce de path del HOST (relativo al repo, o absoluto dentro de él —
    forma natural de escribirlo desde este proyecto) al equivalente DENTRO
    del contenedor (``/home/odoo/<mismo relativo>``): ``scripts/odoo-test``
    valida paths contra ``--addons``, que ya vienen como paths de contenedor
    (ver :func:`resolve_container_addon_paths`). Nombres de módulo sueltos y
    ``all`` pasan sin tocar; un path que ya esté en forma de contenedor, o que
    no exista como directorio del host, también pasa sin tocar (que
    ``scripts/odoo-test`` lo valide y dé su propio error, con su propia lista
    de ``--addons``)."""
    translated = []
    for token in raw_value.split(","):
        stripped = token.strip()
        if stripped and "/" in stripped and not stripped.startswith("/home/odoo/"):
            host_path = (
                stripped if os.path.isabs(stripped)
                else os.path.join(base_path, stripped)
            )
            if os.path.isdir(host_path):
                rel = os.path.relpath(host_path, base_path)
                if not rel.startswith(".."):
                    stripped = f"/home/odoo/{rel}"
        translated.append(stripped)
    return ",".join(translated)


def resolve_container_addon_paths(base_path: str, config: dict, instance: str) -> list[str]:
    """Addon paths of the instance, translated to their path INSIDE the
    container (mounted via ``./src:/home/odoo/src`` in
    ``compose_generator.py``). Equivalent, for ``scripts/odoo-test
    --addons``, of what that script used to resolve itself by reading
    ``instances.json`` directly.
    """
    from generators.config_loader import resolve_instance_config

    inst_conf = config["instances"][instance]
    odoo_conf = resolve_instance_config(inst_conf, config)
    addons = odoo_conf.get("addons", [])
    return [
        f"/home/odoo/{a}" for a in addons
        if os.path.isdir(os.path.join(base_path, a))
    ]


def _resolve_running_service(runner: "Runner", instance: str) -> str | None:
    """Confirm ``odoo-<instance>`` is up and return its Compose service
    name (what ``scripts/odoo-test --container`` actually expects)."""
    service = f"odoo-{instance}"
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "ps", "--status", "running", "--services"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    if service not in result.stdout.split():
        runner.error(f"\n❌ El contenedor '{service}' no está en ejecución.")
        runner.error(f"Prueba iniciando la instancia con: ./odoo start {instance}")
        return None
    return service


def run_tests(
    runner: "Runner", config: dict, base_path: str, instance: str, args: "Namespace"
) -> None:
    """Run ``scripts/odoo-test`` against ``instance`` with the parsed CLI args."""
    container = _resolve_running_service(runner, instance)
    if not container:
        sys.exit(1)

    container_addons = resolve_container_addon_paths(base_path, config, instance)
    if not container_addons:
        runner.error(
            f"\n❌ No se encontraron directorios de addons para la instancia '{instance}'."
        )
        sys.exit(1)

    if args.all_verbose:
        logs_dir = os.path.join(base_path, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        args.out_json = args.out_json or logs_dir
        args.out_coverage_json = args.out_coverage_json or logs_dir
        args.out_logs = args.out_logs or logs_dir
        args.out_verbose = True
        runner.info(f"--all-verbose: guardando reportes en {logs_dir}/")

    cmd = [
        str(Path(base_path) / "scripts" / "odoo-test"),
        args.module,
        "--container", container,
        "--addons", ",".join(container_addons),
    ]
    if args.db:
        cmd += ["-d", args.db]
    if args.tags != "all":
        cmd += ["--tags", args.tags]
    if args.recursive:
        cmd.append("--recursive")
    if args.exclude:
        cmd += ["--exclude", args.exclude]
    if args.no_rm_db:
        cmd.append("--no-rm-db")
    if args.out_coverage_json:
        cmd += ["--out-coverage-json", args.out_coverage_json]
    if args.out_json:
        cmd += ["--out-json", args.out_json]
    if args.out_logs:
        cmd += ["--out-logs", args.out_logs]
    if args.out_verbose:
        cmd.append("--out-verbose")
    if args.dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


__all__ = ["resolve_container_addon_paths", "run_tests"]
