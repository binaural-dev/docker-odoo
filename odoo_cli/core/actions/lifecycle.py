"""Lifecycle actions: build, start, stop, restart, remove.

These are the "modify container state" actions. They share the same
shape: emit a banner via ``runner.info``/``runner.warn``, run one or
more ``docker compose`` subprocesses through ``runner.run_streamed``,
and report back via the runner.

Subprocess choice
-----------------
``runner.run_streamed`` is used for everything that produces stdout
the user wants to see (build logs, container status, ...). It captures
the output so we can stream it line-by-line and then returns the
returncode. ``runner.run_interactive`` is reserved for commands that
take over the TTY (bash, psql) — those live in
:mod:`odoo_cli.core.actions.access`.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from odoo_cli.core.instance import (
    get_db_services,
    get_instance_services,
)
from odoo_cli.core.cli_runner import CliRunner

# Compose file used by ``./odoo``'s ``_docker_compose`` helper. We
# re-create the helper here as a module-level function so callers can
# pass any ``Runner``; the constant must match the legacy CLI.
COMPOSE_FILE = "docker-compose.generated.yml"


def _docker_compose(runner: "Runner", *args: str) -> int:
    """Run ``docker compose -f COMPOSE_FILE <args>`` and stream its output.

    Echoes the command first (so the user can see what's about to
    run) and then delegates to ``runner.run_interactive`` so the
    subprocess inherits our stdout. We deliberately do NOT use
    ``run_streamed`` here: the docker compose CLI produces its own
    progress bars and TTY-aware output, and capturing that into a
    Python buffer would mangle it (no TTY → no progress, no colors).
    """
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]
    runner.info(" ".join(cmd))
    return runner.run_interactive(cmd, cwd=".")


# ============================================================
# Build
# ============================================================


def build_odoo(runner: "Runner", config: dict, no_cache: bool) -> None:
    """Generate all config files and build Docker images."""
    runner.info("\n=== 🛠️  GENERANDO CONFIGURACIONES Y CONSTRUYENDO IMÁGENES ===\n")

    # Imported here (not at module top) so that ``odoo_cli.core.actions.lifecycle``
    # can be imported without sys.path tweaks — the generators module
    # lives in ``./.resources`` which is added to sys.path by the
    # launchers (``./odoo``, ``./odoo-tui``).
    from generators.dockerfile_generator import generate_dockerfiles
    from generators.compose_generator import generate_compose
    from generators.nginx_generator import generate_nginx_config
    from generators.config_loader import get_unique_odoo_versions

    # 1. Generate Dockerfiles for each unique Odoo version
    unique_versions = get_unique_odoo_versions(config)
    runner.info(
        f"Versiones de Odoo detectadas: {', '.join(sorted(unique_versions))}"
    )
    base_path = "."  # cwd is the repo root in the ./odoo launcher
    dockerfile_map = generate_dockerfiles(base_path, unique_versions)

    # 2. Generate docker-compose.generated.yml
    generate_compose(base_path, config, dockerfile_map)

    # 3. Generate nginx config
    generate_nginx_config(base_path, config)

    # 4. Build images
    runner.info("\n=== Construyendo imágenes Docker ===\n")
    if no_cache:
        _docker_compose(runner, "build", "--no-cache")
    else:
        _docker_compose(runner, "build")

    runner.info("\n✅ Build completado.\n")


# ============================================================
# Start / Stop / Restart
# ============================================================


def start_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Start database(s), Odoo instance(s), and nginx."""
    if instance:
        runner.info(f"\n=== ▶️  INICIANDO INSTANCIA: {instance.upper()} ===\n")
    else:
        runner.info("\n=== ▶️  INICIANDO TODAS LAS INSTANCIAS ===\n")

    db_services = get_db_services(config, instance)
    odoo_services = get_instance_services(config, instance)

    # Start managed DBs
    if db_services:
        runner.info("→ Iniciando base(s) de datos...")
        _docker_compose(runner, "up", "-d", *db_services)

    # Start Odoo instances
    runner.info("\n→ Iniciando instancia(s) Odoo...")
    _docker_compose(runner, "up", "-d", *odoo_services)

    # Fix filestore permissions
    for svc in odoo_services:
        try:
            subprocess.run(
                [
                    "docker", "exec", "-u", "root", svc,
                    "chown", "-R", "odoo:odoo", "/home/odoo/data",
                ],
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # Start nginx
    runner.info("\n→ Iniciando Nginx...")
    subprocess.run(["docker", "rm", "-f", "odoo-nginx"], stderr=subprocess.DEVNULL)
    _docker_compose(runner, "up", "-d", "nginx")

    # Show URLs
    runner.info("\n✅ Instancias en ejecución:\n")
    instances_to_show = [instance] if instance else config["instances"].keys()
    for name in instances_to_show:
        port = config["instances"][name]["external_port"]
        runner.info(f"  • {name}: http://localhost:{port}")

    runner.info("")


def stop_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Stop Odoo instance(s) and optionally their databases."""
    if instance:
        runner.warn(f"\n=== ⏹️  DETENIENDO INSTANCIA: {instance.upper()} ===\n")
        odoo_services = get_instance_services(config, instance)
        _docker_compose(runner, "stop", *odoo_services)
        # Check if the DB is still used by other running instances
        db_name = config["instances"][instance]["database"]
        db_conf = config["databases"][db_name]
        if db_conf.get("create_container", True):
            other_users = [
                name for name, conf in config["instances"].items()
                if conf["database"] == db_name and name != instance
            ]
            if not other_users:
                runner.info(
                    f"\n→ Deteniendo base de datos {db_name} "
                    f"(sin otras instancias que la usen)..."
                )
                _docker_compose(runner, "stop", f"db-{db_name}")
            else:
                runner.info(
                    f"\n→ Base de datos {db_name} no se detiene "
                    f"(usada por: {', '.join(other_users)})"
                )
    else:
        runner.warn("\n=== ⏹️  DETENIENDO TODAS LAS INSTANCIAS ===\n")
        _docker_compose(runner, "down")

    runner.info("\n🛑 Detenido.\n")


def restart_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Restart Odoo instance(s)."""
    if instance:
        runner.info(f"\n=== 🔄 REINICIANDO INSTANCIA: {instance.upper()} ===\n")
    else:
        runner.info("\n=== 🔄 REINICIANDO TODAS LAS INSTANCIAS ===\n")
    stop_odoo(runner, config, instance)
    start_odoo(runner, config, instance)


# ============================================================
# Remove
# ============================================================


def remove_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Remove containers and volumes.

    Asks the user for confirmation first. If the user agrees, removes
    the requested instance (or everything, when ``instance`` is None)
    and offers to bring the environment back up blank.
    """
    if instance:
        target = f"instancia '\033[91m{instance}\033[0m'"
    else:
        target = "\033[91mTODAS\033[0m las instancias y bases de datos"

    runner.warn(
        f"\n⚠️  \033[1mPELIGRO\033[0m: Esto eliminará {target} "
        f"y sus volúmenes de datos."
    )
    if not runner.confirm(
        "¿Estás seguro de que deseas continuar?", default=False
    ):
        runner.info("\nOperación cancelada.")
        return

    if instance:
        odoo_services = get_instance_services(config, instance)
        for svc in odoo_services:
            subprocess.run(
                [
                    "docker", "compose", "-f", COMPOSE_FILE,
                    "rm", "-s", "-v", "-f", svc,
                ]
            )
    else:
        _docker_compose(runner, "down", "-v", "--remove-orphans")

    runner.info("\n🛑 Eliminado.\n")

    if runner.confirm(
        "¿Deseas levantar el entorno nuevamente en blanco?", default=True
    ):
        start_odoo(runner, config, instance)


# ============================================================
# Filestore fix
# ============================================================


def fix_filestore(runner: "Runner", config: dict, instance: str | None) -> None:
    """Fix filestore ownership on the target instance(s)."""
    if instance:
        runner.warn(
            f"\n=== 🔧 CORRIGIENDO PERMISOS: {instance.upper()} ===\n"
        )
    else:
        runner.warn(
            "\n=== 🔧 CORRIGIENDO PERMISOS EN TODAS LAS INSTANCIAS ===\n"
        )

    services = get_instance_services(config, instance)
    for svc in services:
        runner.info(f"→ Corrigiendo permisos en {svc}...")
        try:
            subprocess.run(
                [
                    "docker", "exec", "-u", "root", svc,
                    "chown", "-R", "odoo:odoo", "/home/odoo/data",
                ],
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
    runner.info("\n✅ Permisos corregidos.\n")


__all__ = [
    "build_odoo",
    "fix_filestore",
    "remove_odoo",
    "restart_odoo",
    "start_odoo",
    "stop_odoo",
]
