"""Validation of ``instances.json``.

The legacy ``./odoo validate-instances`` subcommand and the
``main()`` pre-dispatch check both call into this module. Keeping the
validation logic in one place means the dispatch path is the only
caller, and the rules (no duplicate ports, every instance references
a defined database) are documented next to the code that enforces
them.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


def validate_instances(runner: "Runner", config: dict) -> None:
    """Validate ``instances.json`` for duplicate ports and valid configuration.

    Reports errors through ``runner.error`` and exits with status 1 on
    the first batch of problems. The function does not return on
    failure (``SystemExit``); on success it returns ``None``.
    """
    ports_seen: dict[int, str] = {}
    errors: list[str] = []

    # Check database ports (host-side). Multiple DBs sharing the same host port
    # is the most common multi-instance pitfall: only one can bind it.
    for db_name, db_conf in config.get("databases", {}).items():
        port = db_conf.get("port")
        if not port:
            continue
        if port in ports_seen:
            errors.append(
                f"Puerto duplicado: {port} usado por la base '{db_name}' "
                f"y '{ports_seen[port]}'"
            )
        else:
            ports_seen[port] = f"base de datos '{db_name}'"

    # Check pgadmin port
    if config.get("pgadmin", {}).get("enabled"):
        port = config["pgadmin"].get("port")
        if port:
            if port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {port} usado por 'pgadmin' "
                    f"y '{ports_seen[port]}'"
                )
            else:
                ports_seen[port] = "pgadmin"

    # Check mailhog http_port (web UI exposed on the host)
    if config.get("mailhog", {}).get("enabled"):
        port = config["mailhog"].get("http_port")
        if port:
            if port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {port} usado por 'mailhog' "
                    f"y '{ports_seen[port]}'"
                )
            else:
                ports_seen[port] = "mailhog"

    # Check instances
    for name, inst in config.get("instances", {}).items():
        # Check external_port
        ext_port = inst.get("external_port")
        if ext_port:
            if ext_port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {ext_port} usado por '{name}' "
                    f"y '{ports_seen[ext_port]}'"
                )
            else:
                ports_seen[ext_port] = f"instancia {name} (external_port)"

        # Check longpolling_port
        lp_port = inst.get("longpolling_port")
        if lp_port:
            if lp_port in ports_seen:
                errors.append(
                    f"Puerto duplicado: {lp_port} usado por '{name}' "
                    f"y '{ports_seen[lp_port]}'"
                )
            else:
                ports_seen[lp_port] = f"instancia {name} (longpolling_port)"

        # Check db existence
        db_name = inst.get("database")
        if db_name and db_name not in config.get("databases", {}):
            errors.append(
                f"La instancia '{name}' usa la base de datos '{db_name}' "
                f"que no está definida en 'databases'."
            )

    if errors:
        runner.error("\n=== ❌ ERROR DE VALIDACIÓN EN instances.json ===\n")
        for err in errors:
            runner.error(f"  - {err}")
        runner.error("")
        sys.exit(1)


def _collect_config_ports(config: dict) -> set[int]:
    """Every host-side port this ``instances.json`` wants to bind."""
    ports: set[int] = set()

    for db_conf in config.get("databases", {}).values():
        if db_conf.get("port"):
            ports.add(db_conf["port"])

    if config.get("pgadmin", {}).get("enabled"):
        if config["pgadmin"].get("port"):
            ports.add(config["pgadmin"]["port"])

    if config.get("mailhog", {}).get("enabled"):
        if config["mailhog"].get("http_port"):
            ports.add(config["mailhog"]["http_port"])

    for inst in config.get("instances", {}).values():
        if inst.get("external_port"):
            ports.add(inst["external_port"])
        if inst.get("longpolling_port"):
            ports.add(inst["longpolling_port"])

    return ports


def check_host_port_collisions(
    runner: "Runner", config: dict, compose_file: str = "docker-compose.generated.yml"
) -> None:
    """Warn (never block) if a wanted port is already held by a container
    from a *different* Compose project running on this host.

    ``validate_instances`` only catches duplicate ports *within* this one
    ``instances.json`` — it has no way to see a second, separate
    docker-odoo checkout on the same machine. This looks at the actual
    Docker state instead: any port we want that's already published by a
    container outside our own project is very likely another deployment
    reusing the same port (a common copy-paste-from-example mistake),
    which would otherwise only surface as a cryptic "address already in
    use" from Docker itself.

    Best-effort: if the Docker daemon isn't reachable (or ``docker`` isn't
    installed), this silently does nothing — Docker's own bind-conflict
    error remains the final safety net either way.
    """
    wanted_ports = _collect_config_ports(config)
    if not wanted_ports:
        return

    try:
        own = subprocess.run(
            ["docker", "compose", "-f", compose_file, "ps", "-q"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        all_containers = subprocess.run(
            # --no-trunc is load-bearing: `docker compose ps -q` prints
            # full 64-char IDs, while `docker ps` truncates {{.ID}} to 12
            # chars. Without it no container ever matches `own_ids` and
            # every one of *our* containers gets reported as a foreign
            # deployment.
            ["docker", "ps", "--no-trunc", "--format", "{{.ID}}\t{{.Names}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return

    if all_containers.returncode != 0 or own.returncode != 0:
        # Without a reliable list of our own containers we can't tell
        # ours from theirs — staying quiet beats warning about ourselves.
        return

    own_ids = set(own.stdout.split())

    conflicts: list[tuple[str, list[int]]] = []
    for line in all_containers.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        container_id, name, ports_str = parts
        if container_id in own_ids:
            continue
        host_ports = {int(p) for p in re.findall(r":(\d+)->", ports_str)}
        hit = wanted_ports & host_ports
        if hit:
            conflicts.append((name, sorted(hit)))

    if conflicts:
        runner.warn(
            "\n⚠️  Posible colisión de puertos con OTRO despliegue/proyecto "
            "de Docker ya corriendo en este host (no es el nuestro):"
        )
        for name, ports in conflicts:
            runner.warn(
                f"  - '{name}' ya está usando el/los puerto(s): "
                f"{', '.join(str(p) for p in ports)}"
            )
        runner.warn(
            "  Si son dos checkouts distintos de docker-odoo, revisá que "
            "no reutilicen los mismos valores de external_port/database "
            "port/pgadmin/mailhog en instances.json.\n"
        )
