"""
Loads and validates instances.json configuration.
Resolves odoo_config references and applies overwrite_odoo_config merges.
"""

import json
import os
import sys


def _strip_json_comments(text: str) -> str:
    """Remove ``//`` comments from JSON-like text, preserving them inside strings.

    The team's ``instances.json`` is documented inline with ``//`` comments
    (like JSON5/JSONC). Python's :func:`json.load` does NOT understand those,
    so we strip them here before parsing.

    The parser walks the text char-by-char and is aware of:

    * single- and double-quoted strings (``"..."`` and ``'...'``)
    * escaped quotes inside strings (``\\"``)
    * line comments starting with ``//`` outside of strings

    Anything between an opening quote and its matching closing quote is kept
    verbatim, even if it contains ``//`` (e.g. ``"https://example.com"``).
    """
    out = []
    i = 0
    n = len(text)
    in_string = False
    string_char = None

    while i < n:
        ch = text[i]

        # Start of a string literal.
        if not in_string and ch in ('"', "'"):
            in_string = True
            string_char = ch
            out.append(ch)
            i += 1
            continue

        # Inside a string: handle escapes and end of string.
        if in_string:
            if ch == '\\' and i + 1 < n:
                # Preserve escape sequence (e.g. \" or \\).
                out.append(ch)
                out.append(text[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
                string_char = None
            out.append(ch)
            i += 1
            continue

        # Outside a string: detect // line comment.
        if ch == '/' and i + 1 < n and text[i + 1] == '/':
            # Skip until end of line (but keep the newline).
            while i < n and text[i] != '\n':
                i += 1
            continue

        out.append(ch)
        i += 1

    return ''.join(out)


def load_config(base_path):
    """Load instances.json from the project root and filter enabled ones."""
    config_path = os.path.join(base_path, "instances.json")
    if not os.path.exists(config_path):
        print(f"Error: instances.json no encontrado en {base_path}")
        print("Copia instances.example.json a instances.json y configúralo.")
        sys.exit(1)

    with open(config_path, "r") as f:
        raw = f.read()
    config = json.loads(_strip_json_comments(raw))

    # Filter instances: keep only those with "enabled": true (or without the flag)
    if "instances" in config:
        config["instances"] = {
            name: inst
            for name, inst in config["instances"].items()
            if inst.get("enabled", True)
        }

    _validate_config(config)
    return config


def load_full_config(base_path):
    """Load instances.json from the project root WITHOUT filtering.

    Use this when the caller needs to see / toggle the ``enabled`` flag
    (e.g. the interactive TUI). For dispatch paths (./odoo CLI, generators)
    prefer :func:`load_config`, which enforces the enabled filter.

    The same validation as ``load_config`` is applied to the unfiltered
    structure so that downstream resolvers don't see inconsistent data.
    """
    config_path = os.path.join(base_path, "instances.json")
    if not os.path.exists(config_path):
        print(f"Error: instances.json no encontrado en {base_path}")
        print("Copia instances.example.json a instances.json y configúralo.")
        sys.exit(1)

    with open(config_path, "r") as f:
        raw = f.read()
    config = json.loads(_strip_json_comments(raw))

    _validate_config(config)
    return config


def is_instance_enabled(inst_conf) -> bool:
    """Return whether an instance config block is enabled.

    Defaults to ``True`` when the flag is missing, matching the behaviour
    of :func:`load_config`.
    """
    return inst_conf.get("enabled", True)


def _validate_config(config):
    """Validate the configuration structure."""
    required_sections = ["odoo_configs", "databases", "instances"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Sección '{section}' requerida en instances.json")

    if not config["instances"]:
        raise ValueError("Debe haber al menos una instancia definida")

    # Validate each database
    for db_name, db_conf in config["databases"].items():
        _validate_database(db_name, db_conf)

    # Validate each instance
    for inst_name, inst_conf in config["instances"].items():
        _validate_instance(inst_name, inst_conf, config)


def _validate_database(db_name, db_conf):
    """Validate a database configuration."""
    required = ["postgres_version", "port", "user", "password"]
    for field in required:
        if field not in db_conf:
            raise ValueError(
                f"Database '{db_name}': campo '{field}' requerido"
            )

    create_container = db_conf.get("create_container", True)
    if not create_container and "host" not in db_conf:
        raise ValueError(
            f"Database '{db_name}': 'host' requerido cuando create_container=false"
        )


def _validate_instance(inst_name, inst_conf, config):
    """Validate an instance configuration."""
    required = ["odoo_version", "external_port", "database", "odoo_config"]
    for field in required:
        if field not in inst_conf:
            raise ValueError(
                f"Instancia '{inst_name}': campo '{field}' requerido"
            )

    # Validate references
    if inst_conf["database"] not in config["databases"]:
        raise ValueError(
            f"Instancia '{inst_name}': database '{inst_conf['database']}' "
            f"no existe en la sección databases"
        )

    if inst_conf["odoo_config"] not in config["odoo_configs"]:
        raise ValueError(
            f"Instancia '{inst_name}': odoo_config '{inst_conf['odoo_config']}' "
            f"no existe en la sección odoo_configs"
        )

    # Validate unique external_port
    ports = [
        v["external_port"]
        for k, v in config["instances"].items()
    ]
    if len(ports) != len(set(ports)):
        raise ValueError("Los external_port de las instancias deben ser únicos")


def resolve_instance_config(inst_conf, config):
    """
    Resolve the effective odoo config for an instance.
    Takes the base odoo_config and applies overwrite_odoo_config on top.
    """
    base_config_name = inst_conf["odoo_config"]
    base_config = dict(config["odoo_configs"][base_config_name])

    overwrite = inst_conf.get("overwrite_odoo_config", {})
    base_config.update(overwrite)

    return base_config


def resolve_db_config(inst_conf, config):
    """Resolve the database configuration for an instance."""
    db_name = inst_conf["database"]
    return config["databases"][db_name]


def get_db_host(db_name, db_conf):
    """
    Get the DB host for a given database config.
    For managed DBs, returns the container name (resolved by Docker's internal
    DNS so the Odoo container talks to the postgres container directly — no
    host port forwarding involved).
    For external DBs, returns the host.
    """
    create_container = db_conf.get("create_container", True)
    if create_container:
        return f"db-{db_name}"
    return db_conf["host"]


def get_db_internal_port(db_conf):
    """Return the port Postgres listens on *inside* its container.

    ``db_conf['port']`` is the **host-side** port (used for
    ``docker-compose.ports: "<port>:5432"``). Containers always talk
    to Postgres via its internal listener, which for the
    ``postgres:<major>`` images is 5432.

    Use this from CLI helpers (``odoo pw``, ``odoo_restore``,
    ``psql_connect``) that run ``docker exec`` inside the Odoo
    container and need to reach Postgres through the Docker network.
    External databases may override via ``db_conf['internal_port']``.
    """
    return int(db_conf.get("internal_port", 5432))


def get_unique_odoo_versions(config):
    """Get the set of unique Odoo versions across all instances."""
    return set(
        inst["odoo_version"]
        for inst in config["instances"].values()
    )


def get_managed_databases(config):
    """Get databases that need a container (create_container=true or default)."""
    return {
        name: conf
        for name, conf in config["databases"].items()
        if conf.get("create_container", True)
    }


def get_odoo_minor(odoo_version):
    """Extract the minor version number from odoo_version string."""
    if odoo_version == "master":
        return "master"
    return odoo_version.split(".")[0]
