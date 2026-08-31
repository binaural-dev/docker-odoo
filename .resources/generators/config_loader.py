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


def is_production_instance(inst_conf) -> bool:
    """Return whether an instance is flagged as production.

    Defaults to ``False`` (non-production) when the flag is missing.
    Used to gate destructive CLI actions (see ``remove_odoo``) and to
    forbid ``dev_mode`` from ever reaching a production container.
    """
    return bool(inst_conf.get("production", False))


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

    _validate_cron_dbfilter_isolation(config)


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

    # Validate 'production' flag type and its interaction with 'dev_mode'.
    # A typo'd non-bool value here would silently defeat the remove_odoo
    # safety gate (is_production_instance), so reject it outright rather
    # than coercing it.
    if "production" in inst_conf and not isinstance(inst_conf["production"], bool):
        raise ValueError(
            f"Instancia '{inst_name}': 'production' debe ser true/false, "
            f"no {inst_conf['production']!r}"
        )

    odoo_conf = resolve_instance_config(inst_conf, config)
    if odoo_conf.get("dev_mode", False) and is_production_instance(inst_conf):
        raise ValueError(
            f"Instancia '{inst_name}': 'dev_mode' no puede estar activo junto a "
            f"'production': true (usá './odoo update' en su lugar)."
        )

    # Validate unique external_port
    ports = [
        v["external_port"]
        for k, v in config["instances"].items()
    ]
    if len(ports) != len(set(ports)):
        raise ValueError("Los external_port de las instancias deben ser únicos")


def _validate_cron_dbfilter_isolation(config):
    """Odoo NO aplica 'dbfilter' al ejecutar cron (ir.cron) -- confirmado
    leyendo el codigo fuente real de Odoo 14.0/16.0/17.0/19.0. 'dbfilter'
    solo rige el ruteo HTTP (selector de bases, sesion). Cuando varias
    instancias comparten un mismo servicio de Postgres, el cron de una
    puede terminar procesando (y modificando) datos de las bases de las
    OTRAS instancias -- esto ya paso en produccion
    (integra-maintenance-comercial-19.0.1 -> integra-maintenance-19.0.1,
    ambas sobre 'pg16').

    La proteccion real es a nivel de Postgres, no de Odoo: cada instancia
    necesita su PROPIO rol (dueno solo de sus propias bases), asi el filtro
    nativo de list_dbs() (datdba=current_user) ya alcanza sin tocar cron.
    Por eso, cuando >1 instancia comparte 'database' y el cron esta activo
    (max_cron_threads != 0), cada instancia del grupo DEBE tener:
      - un 'db_filter' especifico (no vacio, no '*', sin placeholders
        %h/%d -- el cron no tiene un host de request que resolver), Y
      - credenciales propias ('db_user'/'db_password' a nivel de instancia,
        no heredadas del servicio de base de datos compartido) -- sin esto,
        el db_filter por si solo no aisla nada a nivel de Postgres.

    Escape hatch legitimo: 'max_cron_threads': 0 (instancia sin cron, sin
    este riesgo, no exige nada de lo anterior)."""
    from collections import defaultdict

    groups = defaultdict(list)
    for inst_name, inst_conf in config["instances"].items():
        groups[inst_conf["database"]].append(inst_name)

    for db_name, inst_names in groups.items():
        if len(inst_names) <= 1:
            continue

        filter_violations = []
        placeholder_violations = []
        credential_violations = []
        for inst_name in inst_names:
            inst_conf = config["instances"][inst_name]
            odoo_conf = resolve_instance_config(inst_conf, config)
            db_filter = odoo_conf.get("db_filter") or ""
            max_cron_threads = odoo_conf.get("max_cron_threads", 1)

            if max_cron_threads == 0:
                continue  # escape hatch legitimo: sin cron, sin riesgo

            if not db_filter or db_filter == "*":
                filter_violations.append(inst_name)
            elif "%h" in db_filter or "%d" in db_filter:
                placeholder_violations.append(inst_name)

            if not inst_conf.get("db_user") or not inst_conf.get("db_password"):
                credential_violations.append(inst_name)

        # 'db_user' debe identificar un rol REALMENTE distinto por instancia
        # -- esto se chequea para todo el grupo, sin el escape hatch de
        # max_cron_threades: 0, porque un rol compartido por error rompe el
        # aislamiento de Postgres (ambas instancias terminan viendo/pudiendo
        # tocar la union de las bases de las dos) independientemente de si
        # alguna corre cron o no.
        db_users_seen = defaultdict(list)
        for inst_name in inst_names:
            db_user = config["instances"][inst_name].get("db_user")
            if db_user:
                db_users_seen[db_user].append(inst_name)

        duplicate_role_violations = {
            db_user: insts for db_user, insts in db_users_seen.items() if len(insts) > 1
        }

        shared_service_user = config["databases"][db_name].get("user")
        reused_shared_role_violations = [
            inst_name for inst_name in inst_names
            if config["instances"][inst_name].get("db_user") == shared_service_user
            and shared_service_user
        ]

        if not (filter_violations or placeholder_violations or credential_violations
                or duplicate_role_violations or reused_shared_role_violations):
            continue

        lines = [
            f"Instancia(s) inseguras compartiendo el servicio de base de "
            f"datos '{db_name}' (grupo: {', '.join(inst_names)}):",
            "",
        ]

        if filter_violations:
            lines += [
                "Sin 'db_filter' especifico:",
                *(f"  - {n}" for n in filter_violations),
                "",
            ]

        if placeholder_violations:
            lines += [
                "'db_filter' usa %h/%d (placeholders de host, no resolubles "
                "desde cron -- no hay una peticion HTTP detras):",
                *(f"  - {n}" for n in placeholder_violations),
                "",
            ]

        if credential_violations:
            lines += [
                "Sin 'db_user'/'db_password' propios (dependen del rol "
                "compartido del servicio, sin aislamiento real de Postgres):",
                *(f"  - {n}" for n in credential_violations),
                "",
            ]

        if duplicate_role_violations:
            lines += ["'db_user' repetido entre instancias del mismo grupo (no son roles realmente distintos -- Postgres ve un solo rol, dueno de la union de bases de ambas):"]
            for db_user, insts in duplicate_role_violations.items():
                lines.append(f"  - '{db_user}' usado por: {', '.join(insts)}")
            lines.append("")

        if reused_shared_role_violations:
            lines += [
                f"'db_user' igual al rol compartido del servicio ('{shared_service_user}') -- no es un rol dedicado, es el mismo que ya usan las demas instancias sin credenciales propias:",
                *(f"  - {n}" for n in reused_shared_role_violations),
                "",
            ]

        lines += [
            "Por que las dos cosas son obligatorias juntas: Odoo NO aplica "
            "'dbfilter' al ejecutar cron (ir.cron), solo al ruteo HTTP -- ya "
            "paso en produccion que el cron de una instancia proceso datos "
            "de la base de OTRA instancia del mismo servicio "
            "(integra-maintenance-comercial-19.0.1 -> "
            "integra-maintenance-19.0.1). La proteccion real es que cada "
            "instancia tenga su PROPIO rol de Postgres, dueno solo de sus "
            "propias bases -- eso tambien evita que una base de una version "
            "de Odoo (ej. 17.0) termine usandose desde una instancia de otra "
            "version (ej. 19.0).",
            "",
            "Para arreglar cada instancia listada arriba, en su nivel raiz "
            "(no dentro de overwrite_odoo_config):",
            "  - Agregar 'db_user'/'db_password' con un rol dedicado (distinto "
            "al de cualquier otra instancia del grupo y al rol compartido del "
            "servicio), y un 'db_filter' especifico en overwrite_odoo_config "
            "(ej. '^integra\\-17\\.0'). Correr el aprovisionamiento del rol "
            "antes de levantar la instancia con esas credenciales.",
            "  - O, si esta instancia NO debe correr cron (solo se usa para "
            "explorar otra base), poner 'max_cron_threads': 0 explicitamente "
            "en overwrite_odoo_config -- deja constancia de que es "
            "intencional, no un olvido.",
        ]

        raise ValueError("\n".join(lines))


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
    """Resolve the database configuration for an instance.

    An instance can optionally connect with its own dedicated Postgres role
    (see 'provision-role') instead of the role shared by every instance on
    this database service. When 'db_user'/'db_password' are set at the
    instance's root level, they override the service-level 'user'/'password'
    here so every consumer (compose generation, 'pw', 'psql', ...) resolves
    to the same credentials without duplicating this fallback logic. Falls
    back to the service-level role when not set, so existing instances are
    unaffected.
    """
    db_name = inst_conf["database"]
    db_conf = config["databases"][db_name]
    if "db_user" in inst_conf or "db_password" in inst_conf:
        db_conf = {
            **db_conf,
            "user": inst_conf.get("db_user", db_conf["user"]),
            "password": inst_conf.get("db_password", db_conf["password"]),
        }
    return db_conf


def get_db_host(db_name, db_conf):
    """
    Get the DB host for a given database config.
    For managed DBs, returns the container name (reachable via Docker's
    internal DNS on the shared network — no host port forwarding involved).
    For external DBs, returns the host.
    """
    create_container = db_conf.get("create_container", True)
    if create_container:
        return f"db-{db_name}"
    return db_conf["host"]


def get_db_internal_port(db_conf):
    """Return the port Postgres listens on *inside* its container.

    ``db_conf['port']`` is the **host-side** port used only when
    ``expose_host_port`` is enabled (``ports: "<port>:5432"`` in compose).
    Containers always talk to Postgres over the internal Docker network,
    where the postgres image listens on 5432 regardless of the host
    mapping. Use this from CLI helpers (``odoo pw``, ``odoo_restore``,
    ``psql_connect``) that run ``docker exec`` inside the Odoo container,
    and anything else that connects to Postgres from another container.
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
    """Get databases that need a container (create_container=true or default),
    restricted to those actually referenced by an active (enabled) instance.
    """
    used_db_names = {inst["database"] for inst in config["instances"].values()}
    return {
        name: conf
        for name, conf in config["databases"].items()
        if conf.get("create_container", True) and name in used_db_names
    }


def get_odoo_minor(odoo_version):
    """Extract the minor version number from odoo_version string."""
    if odoo_version == "master":
        return "master"
    return odoo_version.split(".")[0]
