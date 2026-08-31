"""Access actions: bash, logs, list, psql.

These are the "interact with a running instance" actions. They use
``runner.run_interactive`` for the ones that take over the TTY
(bash, psql) and ``runner.run_streamed`` for the ones whose output
the user just watches (logs, list).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from odoo_cli.core.instance import get_db_services, get_instance_services
from odoo_cli.core.actions.lifecycle import COMPOSE_FILE, _docker_compose  # noqa: F401


# ============================================================
# Bash
# ============================================================


def run_bash(runner: "Runner", config: dict, instance: str) -> None:
    """Open bash in an Odoo instance container.

    If the service is not running, prints a helpful hint and returns.
    Otherwise delegates to ``docker compose exec -it ... bash`` through
    ``runner.run_interactive`` so the TTY stays connected.

    Uses ``docker compose exec`` (by service name) rather than plain
    ``docker exec``/``docker inspect`` against a container name: the
    real container name is namespaced by the Compose project and is
    no longer guaranteed to equal ``odoo-<instance>``.
    """
    service = f"odoo-{instance}"
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "ps", "--status", "running", "--services"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    running_services = result.stdout.split()

    if service not in running_services:
        runner.error(
            f"\n❌ El contenedor '{service}' no está en ejecución."
        )
        runner.error(
            f"Prueba iniciando la instancia con: ./odoo start {instance}"
        )
        return

    runner.info(f"\n=== 🐚 ABRIENDO BASH EN: {instance.upper()} ===\n")
    runner.run_interactive(
        ["docker", "compose", "-f", COMPOSE_FILE, "exec", "-u", "root", "-it", service, "bash"],
        cwd=".",
    )


# ============================================================
# Logs
# ============================================================


def show_logs(runner: "Runner", config: dict, instance: str | None) -> None:
    """Show logs for instance(s)."""
    if instance:
        runner.info(f"\n=== 📋 MOSTRANDO LOGS DE: {instance.upper()} ===\n")
        services = get_instance_services(config, instance)
        db_services = get_db_services(config, instance)
        all_services = db_services + services
        _docker_compose(runner, "logs", "--tail=10", "-f", *all_services)
    else:
        runner.info("\n=== 📋 MOSTRANDO TODOS LOS LOGS ===\n")
        _docker_compose(runner, "logs", "--tail=10", "-f")


# ============================================================
# List
# ============================================================


def list_containers(runner: "Runner", config: dict) -> None:
    """List running containers."""
    runner.info("\n=== 🐳 CONTENEDORES EN EJECUCIÓN ===\n")
    _docker_compose(runner, "ps")


# ============================================================
# psql
# ============================================================


def psql_connect(
    runner: "Runner", config: dict, instance: str, dbname: str
) -> None:
    """Connect to psql in an instance."""
    from generators.config_loader import (
        resolve_db_config,
        get_db_host,
        get_db_internal_port,
    )

    inst_conf = config["instances"][instance]
    db_conf = resolve_db_config(inst_conf, config)
    db_host = get_db_host(inst_conf["database"], db_conf)
    db_user = db_conf["user"]
    db_port = get_db_internal_port(db_conf)
    service = f"odoo-{instance}"

    runner.info(
        f"\n=== 🐘 CONECTANDO PSQL A: {instance.upper()} (DB: {dbname}) ===\n"
    )
    runner.run_interactive(
        [
            "docker", "compose", "-f", COMPOSE_FILE, "exec", "-it", service,
            "psql",
            "--host", db_host,
            "--port", str(db_port),
            "-U", db_user,
            "-d", dbname,
        ],
        cwd=".",
    )
    # NOTE: the legacy CLI passed PGPASSWORD via the parent's env
    # (``env={**os.environ, "PGPASSWORD": db_password}``). That env
    # never reached the container's psql — ``docker exec`` does not
    # forward host env vars by default. We drop the no-op here. The
    # user-visible behavior is identical.


__all__ = [
    "list_containers",
    "psql_connect",
    "run_bash",
    "show_logs",
]
