"""Helpers for reading instance/db facts from ``instances.json`` and the running containers.

This is the "what services / databases / users / repos exist" surface.
It is intentionally runner-agnostic: these helpers don't print
anything and don't talk to the user — they only read the config and,
for the DB-side helpers, run a single ``docker exec psql`` round-trip
to ask Postgres.

Why split this from the action modules?
---------------------------------------
The action modules (build, start, psql, ...) need to know which
service name to target (``odoo-<name>``, ``db-<name>``) and which
databases / users exist inside a container. Keeping the lookup logic
here means the action modules stay focused on the *workflow* and not
on the data plumbing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

# Reuse the same module-level base path that ``./odoo`` injects. The
# callers (action modules, dispatch) are expected to pass the project
# base path explicitly when needed; for the repo/custom lookups we
# fall back to a sensible default that lets tests override it.
_DEFAULT_BASE_PATH = os.environ.get("DOCKER_ODOO_BASE_PATH", os.getcwd())

# Must match odoo_cli.core.actions.lifecycle.COMPOSE_FILE. Duplicated here
# (not imported) to avoid a circular import: lifecycle.py already imports
# from this module.
_COMPOSE_FILE = "docker-compose.generated.yml"


# ============================================================
# Service name resolution (pure config lookups)
# ============================================================


def get_instance_services(
    config: dict, instance: str | None = None
) -> list[str]:
    """Return the list of docker compose service names for an instance (or all).

    Raises :class:`SystemExit` if ``instance`` is not present in the
    config. Callers should have already validated the config
    (:func:`odoo_cli.core.actions.validate.validate_instances`).
    """
    if instance:
        if instance not in config["instances"]:
            print(
                f"Error: Instancia '{instance}' no existe en instances.json"
            )
            print(
                f"Instancias disponibles: "
                f"{', '.join(config['instances'].keys())}"
            )
            sys.exit(1)
        return [f"odoo-{instance}"]
    return [f"odoo-{name}" for name in config["instances"]]


def get_db_services(
    config: dict, instance: str | None = None
) -> list[str]:
    """Return the list of managed DB services for an instance (or all enabled).

    Honours the ``create_container`` flag on each database: a DB with
    ``create_container=false`` (i.e. an external Postgres) does not
    produce a service here, because the docker compose file won't have
    a service for it.
    """
    if instance:
        inst_conf = config["instances"][instance]
        db_name = inst_conf["database"]
        db_conf = config["databases"][db_name]
        if db_conf.get("create_container", True):
            return [f"db-{db_name}"]
        return []
    # Only start DBs used by enabled instances
    needed = set()
    for name, inst in config["instances"].items():
        needed.add(inst["database"])
    return [
        f"db-{name}" for name in needed
        if config["databases"].get(name, {}).get("create_container", True)
    ]


# ============================================================
# DB lookups (docker exec psql round-trip)
# ============================================================


def get_databases(config: dict, instance: str) -> list[str]:
    """Fetch database names from the postgres container of an instance.

    Returns ``[]`` on any error (container not running, psql failure,
    network blip, ...). Callers must handle the empty case (typically
    by falling back to manual input).
    """
    # Local import: the generators module is on .resources which is
    # only added to sys.path by the ./odoo launcher.
    from generators.config_loader import (
    resolve_db_config, get_db_host, get_db_internal_port,
)

    try:
        inst_conf = config["instances"][instance]
        db_conf = resolve_db_config(inst_conf, config)
        db_host = get_db_host(inst_conf["database"], db_conf)
        db_user = db_conf["user"]
        db_password = db_conf["password"]
        db_port = get_db_internal_port(db_conf)
        service = f"odoo-{instance}"

        cmd = (
            f"docker compose -f {_COMPOSE_FILE} exec -T "
            f"-e PGPASSWORD={db_password} {service} "
            f"psql --host {db_host} --port {db_port} -U {db_user} "
            f"-d postgres -At -c "
            f"\"SELECT datname FROM pg_database "
            f"WHERE datistemplate = false AND datname NOT IN "
            f"('postgres', 'template1');\" 2>/dev/null"
        )
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        if output:
            return sorted(output.split("\n"))
    except Exception:
        pass
    return []


def get_users(config: dict, instance: str, dbname: str) -> list[str]:
    """Fetch active user logins from a specific database.

    Returns ``[]`` on any error. Caller decides whether to fall back to
    manual input.
    """
    from generators.config_loader import (
    resolve_db_config, get_db_host, get_db_internal_port,
)

    try:
        inst_conf = config["instances"][instance]
        db_conf = resolve_db_config(inst_conf, config)
        db_host = get_db_host(inst_conf["database"], db_conf)
        db_user = db_conf["user"]
        db_password = db_conf["password"]
        db_port = get_db_internal_port(db_conf)
        service = f"odoo-{instance}"

        cmd = (
            f"docker compose -f {_COMPOSE_FILE} exec -T "
            f"-e PGPASSWORD={db_password} {service} "
            f"psql --host {db_host} --port {db_port} -U {db_user} "
            f"-d {dbname} -At -c "
            f"\"SELECT login FROM res_users WHERE active = true "
            f"ORDER BY login;\" 2>/dev/null"
        )
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        if output:
            return sorted(output.split("\n"))
    except Exception:
        pass
    return []


def _instance_has_db(
    instance: str, dbname: str, config: dict
) -> bool:
    """True if ``dbname`` exists in the container of ``instance``.

    Used by the dispatch logic to resolve the instance for ``pw -d``.
    """
    from generators.config_loader import (
    resolve_db_config, get_db_host, get_db_internal_port,
)

    inst_conf = config["instances"][instance]
    db_conf = resolve_db_config(inst_conf, config)
    db_host = get_db_host(inst_conf["database"], db_conf)
    db_user = db_conf["user"]
    db_password = db_conf["password"]
    db_port = get_db_internal_port(db_conf)
    service = f"odoo-{instance}"
    env = {"PGPASSWORD": db_password, "PATH": os.environ.get("PATH", "")}
    proc = subprocess.run(
        [
            "docker", "compose", "-f", _COMPOSE_FILE, "exec", "-T", service,
            "psql",
            "--host", db_host,
            "--port", str(db_port),
            "-U", db_user,
            "-d", "postgres",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{dbname}'",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False
    return "1" in (proc.stdout or "").strip().splitlines()


def find_instances_with_db(config: dict, dbname: str) -> list[str]:
    """Return all instances whose container has ``dbname``."""
    return [
        inst for inst in config["instances"]
        if _instance_has_db(inst, dbname, config)
    ]


# ============================================================
# Custom repos / modules (filesystem-only)
# ============================================================


def get_custom_repos(base_path: str | None = None) -> list[str]:
    """List directories in ``<base_path>/src/custom/``."""
    base = base_path or _DEFAULT_BASE_PATH
    custom_path = os.path.join(base, "src", "custom")
    if not os.path.isdir(custom_path):
        return []
    return sorted([
        d for d in os.listdir(custom_path)
        if os.path.isdir(os.path.join(custom_path, d))
    ])


def get_projects_for_version(
    config: dict, odoo_version: str, base_path: str | None = None
) -> list[str]:
    """Instance names on ``odoo_version`` that have a ``src/custom/<name>`` checkout.

    Instance names map 1:1 to ``src/custom/<name>`` by convention across
    every instance in ``instances.json`` (each instance's first custom
    addon path is its own ``src/custom/<name>``). Instances whose
    project hasn't been cloned locally yet are silently excluded — a
    bulk bump can't touch a repo that doesn't exist on disk.
    """
    existing = set(get_custom_repos(base_path))
    return sorted(
        name
        for name, inst in config["instances"].items()
        if inst["odoo_version"] == odoo_version and name in existing
    )


def get_custom_modules(
    config: dict, instance: str, base_path: str | None = None
) -> list[str]:
    """List custom modules found in the addons paths of an instance."""
    from generators.config_loader import resolve_instance_config

    base = base_path or _DEFAULT_BASE_PATH
    try:
        inst_conf = config["instances"][instance]
        odoo_conf = resolve_instance_config(inst_conf, config)
        addons_paths = odoo_conf.get("addons", [])

        modules = []
        for path in addons_paths:
            full_path = os.path.join(base, path)
            if not os.path.isdir(full_path):
                continue
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isdir(item_path):
                    if (
                        os.path.exists(os.path.join(item_path, "__manifest__.py"))
                        or os.path.exists(os.path.join(item_path, "__openerp__.py"))
                    ):
                        modules.append(item)
        return sorted(list(set(modules)))
    except Exception:
        pass
    return []
