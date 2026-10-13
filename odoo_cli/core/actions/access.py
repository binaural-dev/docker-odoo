"""Access actions: bash, logs, list, psql.

These are the "interact with a running instance" actions. They use
``runner.run_interactive`` for the ones that take over the TTY
(bash, psql) and ``runner.run_streamed`` for the ones whose output
the user just watches (logs, list).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
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


def _running_compose_services() -> dict[str, dict]:
    """Map compose service name -> ``docker compose ps`` JSON row.

    Compose v2.21+ prints one JSON object per line; older versions print
    a single JSON array. Both are accepted.
    """
    import json

    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "ps", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker compose ps falló")

    out = result.stdout.strip()
    if not out:
        return {}
    if out.startswith("["):
        rows = json.loads(out)
    else:
        rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    return {row.get("Service", ""): row for row in rows}


def list_containers(runner: "Runner", config: dict) -> None:
    """List running Odoo instances as an instance/container/port table."""
    try:
        running = _running_compose_services()
    except (RuntimeError, ValueError) as exc:
        runner.error(f"\n❌ Error al listar contenedores: {exc}\n")
        return

    rows = []
    for instance, conf in config.get("instances", {}).items():
        row = running.get(f"odoo-{instance}")
        if row is None:
            continue
        rows.append((
            instance,
            row.get("Name", ""),
            str(conf.get("odoo_version", "")),
            str(conf.get("external_port", "N/A")),
            row.get("Status", "") or row.get("State", ""),
        ))

    headers = ("Instancia", "Contenedor", "Versión", "Puerto", "Estado")
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]

    def fmt(cols):
        return " | ".join(c.ljust(w) for c, w in zip(cols, widths))

    lines = ["", fmt(headers), "-+-".join("-" * w for w in widths)]
    if rows:
        lines += [fmt(r) for r in sorted(rows)]
    else:
        lines.append("No hay instancias de Odoo en ejecución.")
    runner.info("\n".join(lines) + "\n")


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
        resolve_instance_db_creds,
    )

    inst_conf = config["instances"][instance]
    db_conf = resolve_db_config(inst_conf, config)
    db_host = get_db_host(inst_conf["database"], db_conf)
    # Rol dedicado de la instancia si lo tiene: tras ./odoo provision-role
    # el rol compartido del servicio pierde CONNECT sobre sus bases.
    db_user, _db_password = resolve_instance_db_creds(inst_conf, db_conf)
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


# ============================================================
# Shell
# ============================================================


def run_shell(
    runner: "Runner",
    base_path: str,
    instance: str,
    dbname: str,
    user: str | None,
    extra_args: list[str],
) -> int:
    """Delegate to ``scripts/odoo-shell`` for one-shot ops or a REPL.

    ``scripts/odoo-shell`` does not read ``instances.json`` — it takes
    the container name and database as flags and talks to it via raw
    ``docker exec`` (not ``docker compose exec``: the container name
    it needs, ``odoo-<instance>``, is stable regardless of the Compose
    project namespacing). This action just resolves those flags and
    hands off, keeping the TTY attached via ``run_interactive`` since
    the REPL subcommand is fully interactive.
    """
    cmd = [
        str(Path(base_path) / "scripts" / "odoo-shell"),
        "--container", f"odoo-{instance}",
        "--compose-file", COMPOSE_FILE,
        "-d", dbname,
    ]
    if user:
        cmd += ["--user", user]
    cmd += extra_args
    return runner.run_interactive(cmd, cwd=".")


__all__ = [
    "list_containers",
    "psql_connect",
    "run_bash",
    "run_shell",
    "show_logs",
]
