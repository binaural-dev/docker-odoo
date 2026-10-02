"""
Operations the agent exposes over HTTP.

Everything that touches instances.json, git or Docker lives here, so the
Odoo side (micro_saas) never needs the repo mounted nor docker.sock. Every
input coming from the API is validated before it reaches a command, and
commands are always run as argument lists (never through a shell).
"""

import copy
import json
import os
import shutil
import re
import secrets
import subprocess
import sys
import threading

from . import settings

# docker-odoo checkout this agent manages (see settings.docker_odoo_root)
BASE_PATH = settings.docker_odoo_root()
INSTANCES_JSON_PATH = os.path.join(BASE_PATH, "instances.json")
CLI_PATH = os.path.join(BASE_PATH, "odoo")
CUSTOM_ADDONS_ROOT = os.path.join(BASE_PATH, "src", "custom")
COMPOSE_FILE = "docker-compose.generated.yml"

sys.path.insert(0, os.path.join(BASE_PATH, ".resources"))

from generators.config_loader import (  # noqa: E402
    _validate_config, get_unique_odoo_versions, resolve_instance_config,
    resolve_instance_db_scope,
)
from generators.dockerfile_generator import generate_dockerfiles  # noqa: E402
from generators.compose_generator import generate_compose  # noqa: E402
from generators.nginx_generator import generate_nginx_config  # noqa: E402

MAX_OUTPUT = 20000

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
ODOO_VERSION_RE = re.compile(r"^(\d{2}\.0|master)$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
# "." is the instance folder itself, when src/custom/<slug>/ is the repo
REPO_DIR_RE = re.compile(r"^(\.|[A-Za-z0-9_][A-Za-z0-9_.-]{0,99})$")
# path of a repo relative to the docker-odoo root, e.g. src/custom/bp-staging
SERVER_PATH_RE = re.compile(r"^src(/[A-Za-z0-9_.-]+)+$")
MODULE_RE = re.compile(r"^[a-z0-9_]{1,100}$")
DBNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,63}$")
# Dedicated Postgres role of an instance (db_user). './odoo provision-role'
# puts it and its password straight into SQL, and compose_generator writes
# the password unquoted into the YAML: keep both to plain characters
DB_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
DB_PASSWORD_RE = re.compile(r"^[A-Za-z0-9_.-]{12,128}$")
ADDON_PATH_RE = re.compile(r"^src/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")
REPO_URL_RE = re.compile(r"^(https://[A-Za-z0-9.-]+/|git@[A-Za-z0-9.-]+:)[A-Za-z0-9_./~-]+$")
GITHUB_PATH_RE = re.compile(r"^(?:git@github\.com:|https?://github\.com/)(?P<path>.+)$")
CREDENTIALS_IN_URL_RE = re.compile(r"(https?://)[^/@]+@")

# Keys of an instances.json entry that micro_saas is allowed to set. Anything
# else (extra_volumes, enabled, custom mounts...) can only be changed by
# hand on the host, and is preserved as-is on every update.
OWNED_OVERWRITE_KEYS = ("workers", "without_demo", "addons", "db_filter", "max_cron_threads")

# Credentials of removed instances with a dedicated role, kept until they
# are purged: their databases belong to that role, and the shared service
# user can't drop them
REMOVED_ROLES_FILE = os.path.join(settings.VAR_DIR, "removed_instance_roles.json")

# Only one instances.json read-modify-write at a time, and only one image
# build at a time (a build takes minutes and rebuilds every image).
_config_lock = threading.Lock()
_build_lock = threading.Lock()
# provision-role restarts the whole Postgres service: one at a time
_provision_lock = threading.Lock()


class AgentError(Exception):
    """Invalid request: turned into an HTTP 4xx by the API."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def _check(regex, value, label):
    if not isinstance(value, str) or not regex.match(value) or ".." in value:
        raise AgentError(f"{label} inválido: {value!r}")
    return value


# ----------------------------------------------------------------------
# Command execution
# ----------------------------------------------------------------------


def _redact(text, *secrets_):
    for secret in secrets_:
        if secret:
            text = text.replace(secret, "***")
    return CREDENTIALS_IN_URL_RE.sub(r"\1***@", text)


def _run(cmd, timeout=600, cwd=BASE_PATH, redact=(), env=None, input=None):
    shown = _redact(" ".join(cmd), *redact)
    try:
        # Without input, stdin is /dev/null: an interactive prompt of the
        # CLI (e.g. the db_filter drift fix in './odoo build') reads EOF and
        # skips instead of waiting forever
        result = subprocess.run(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout, env=env, input=input,
            stdin=None if input is not None else subprocess.DEVNULL,
        )
        returncode, output = result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired as e:
        returncode, output = -1, f"{e.output or ''}\n[ERROR] Tiempo agotado ({timeout}s)"
    except OSError as e:
        returncode, output = -1, f"[ERROR] No se pudo ejecutar el comando: {e}"
    output = _redact(output, *redact)
    if len(output) > MAX_OUTPUT:
        output = "[...salida truncada...]\n" + output[-MAX_OUTPUT:]
    return {"ok": returncode == 0, "returncode": returncode, "command": shown, "output": output}


def _merge_results(*results):
    return {
        "ok": all(r["ok"] for r in results),
        "returncode": next((r["returncode"] for r in results if not r["ok"]), 0),
        "command": " && ".join(r["command"] for r in results),
        "output": "\n".join(f"$ {r['command']}\n{r['output']}" for r in results),
    }


def _compose(*args, timeout=600):
    return _run(["docker", "compose", "-f", COMPOSE_FILE, *args], timeout=timeout)


# ----------------------------------------------------------------------
# instances.json
# ----------------------------------------------------------------------


def _read_config():
    if not os.path.exists(INSTANCES_JSON_PATH):
        raise AgentError(f"No existe {INSTANCES_JSON_PATH} en el host", 500)
    with open(INSTANCES_JSON_PATH, "r") as f:
        return json.load(f)


def _write_config(config):
    # Same validation './odoo build' applies (on the enabled instances only,
    # like load_config does), so a bad write fails here and not later.
    to_validate = copy.deepcopy(config)
    to_validate["instances"] = {
        name: inst for name, inst in to_validate.get("instances", {}).items()
        if inst.get("enabled", True)
    }
    try:
        _validate_config(to_validate)
    except (ValueError, KeyError) as e:
        raise AgentError(f"instances.json quedaría inválido: {e}")

    tmp_path = INSTANCES_JSON_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, INSTANCES_JSON_PATH)


def _regen_configs(config):
    """First steps of './odoo build' (compose + nginx), without rebuilding images."""
    enabled = copy.deepcopy(config)
    enabled["instances"] = {
        name: inst for name, inst in enabled["instances"].items()
        if inst.get("enabled", True)
    }
    dockerfile_map = generate_dockerfiles(BASE_PATH, get_unique_odoo_versions(enabled))
    generate_compose(BASE_PATH, enabled, dockerfile_map)
    generate_nginx_config(BASE_PATH, enabled)


def _get_instance(slug, config=None):
    _check(SLUG_RE, slug, "Instancia")
    config = config or _read_config()
    inst_conf = config.get("instances", {}).get(slug)
    if inst_conf is None:
        raise AgentError(f"La instancia '{slug}' no existe en instances.json", 404)
    return inst_conf


def _public_entry(inst_conf):
    """Instance entry without secrets (admin_password, db passwords...)."""
    entry = copy.deepcopy(inst_conf)
    for key in list(entry):
        if "password" in key:
            entry[key] = "***"
    overwrite = entry.get("overwrite_odoo_config", {})
    for key in list(overwrite):
        if "password" in key:
            overwrite[key] = "***"
    return entry


def list_instances():
    config = _read_config()
    return {
        "instances": {
            slug: _public_entry(conf) for slug, conf in config.get("instances", {}).items()
        },
        "odoo_configs": sorted(config.get("odoo_configs", {})),
        "databases": sorted(config.get("databases", {})),
    }


def upsert_instance(slug, payload):
    """Create or update an instance entry, merging onto what's already there.

    Only the keys micro_saas owns are overwritten; anything else already in
    the entry (extra_volumes, enabled, absolute addon paths added by hand...)
    is kept.
    """
    _check(SLUG_RE, slug, "Instancia")
    _check(ODOO_VERSION_RE, payload["odoo_version"], "Versión de Odoo")
    _check(KEY_RE, payload["database"], "Base de datos")
    _check(KEY_RE, payload["odoo_config"], "odoo_config")
    port = payload["external_port"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise AgentError(f"external_port inválido: {port!r}")
    workers = payload.get("workers", 2)
    if not isinstance(workers, int) or not 0 <= workers <= 64:
        raise AgentError(f"workers inválido: {workers!r}")
    for addon in payload["addons"]:
        _check(ADDON_PATH_RE, addon, "Ruta de addons")
    db_filter = payload.get("db_filter")
    # './odoo provision-role' puts db_filter inside a SQL string literal
    if db_filter is not None and (len(db_filter) > 200 or "\n" in db_filter or "'" in db_filter):
        raise AgentError("db_filter inválido (sin saltos de línea ni comillas simples)")
    max_cron_threads = payload.get("max_cron_threads")
    if max_cron_threads is not None and (
            not isinstance(max_cron_threads, int) or not 0 <= max_cron_threads <= 64):
        raise AgentError(f"max_cron_threads inválido: {max_cron_threads!r}")
    # db_user: None keeps the current role, "" drops the instance's own
    # credentials (back to the shared service user)
    db_user = payload.get("db_user")
    if db_user:
        _check(DB_ROLE_RE, db_user, "db_user (minúsculas, dígitos y '_', máx. 63)")
    db_password = payload.get("db_password")
    if db_password and not DB_PASSWORD_RE.match(str(db_password)):
        # the value isn't echoed back: it's a password
        raise AgentError("db_password inválido: 12 a 128 caracteres entre letras, dígitos, '_', '.' y '-'")

    with _config_lock:
        config = _read_config()
        if payload["odoo_config"] not in config.get("odoo_configs", {}):
            raise AgentError(f"El preset '{payload['odoo_config']}' no existe en odoo_configs")
        if payload["database"] not in config.get("databases", {}):
            raise AgentError(f"La base de datos '{payload['database']}' no existe en databases")

        existing = config.setdefault("instances", {}).get(slug, {})
        overwrite = dict(existing.get("overwrite_odoo_config", {}))
        extra_addons = [
            addon for addon in overwrite.get("addons", [])
            if addon.startswith("/") and addon not in payload["addons"]
        ]
        overwrite.update({
            "workers": workers,
            "without_demo": bool(payload.get("without_demo", True)),
            "addons": list(payload["addons"]) + extra_addons,
        })
        if db_filter:
            overwrite["db_filter"] = db_filter
        else:
            overwrite.pop("db_filter", None)
        if max_cron_threads is not None:
            overwrite["max_cron_threads"] = max_cron_threads

        entry = dict(existing)
        entry.update({
            "odoo_version": payload["odoo_version"],
            "external_port": port,
            "database": payload["database"],
            "odoo_config": payload["odoo_config"],
            "overwrite_odoo_config": overwrite,
        })
        if payload.get("domain"):
            entry["domain"] = payload["domain"]
        else:
            entry.pop("domain", None)

        if db_user == "":
            entry.pop("db_user", None)
            entry.pop("db_password", None)
        elif db_user:
            entry["db_user"] = db_user
            if db_password:
                entry["db_password"] = db_password
            elif db_user != existing.get("db_user") or not existing.get("db_password"):
                # micro_saas never needs to know it: it lives in instances.json
                entry["db_password"] = secrets.token_urlsafe(24)
        elif db_password:
            if not entry.get("db_user"):
                raise AgentError("db_password requiere db_user")
            entry["db_password"] = db_password

        config["instances"][slug] = entry
        _write_config(config)

    # The role, and the ownership of the databases matching db_filter, only
    # change on Postgres with './odoo provision-role'
    old_filter = existing.get("overwrite_odoo_config", {}).get("db_filter")
    needs_provision = bool(entry.get("db_user")) and (
        entry.get("db_user") != existing.get("db_user")
        or entry.get("db_password") != existing.get("db_password")
        or overwrite.get("db_filter") != old_filter
    )
    return {"instance": _public_entry(entry), "needs_provision": needs_provision}


def delete_instance(slug):
    """Remove the container, drop the entry and regenerate compose/nginx."""
    _check(SLUG_RE, slug, "Instancia")
    results = [_compose("rm", "-s", "-v", "-f", f"odoo-{slug}")]
    with _config_lock:
        config = _read_config()
        if slug in config.get("instances", {}):
            removed = config["instances"].pop(slug)
            _write_config(config)
            if removed.get("db_user") and removed.get("db_password"):
                _save_removed_role(slug, removed)
            _regen_configs(config)
    # Recreate nginx so it stops publishing the freed port
    results.append(_compose("up", "-d", "nginx"))
    return _merge_results(*results)


def _load_removed_roles():
    if not os.path.exists(REMOVED_ROLES_FILE):
        return {}
    with open(REMOVED_ROLES_FILE) as f:
        return json.load(f)


def _store_removed_roles(data):
    os.makedirs(os.path.dirname(REMOVED_ROLES_FILE), exist_ok=True)
    tmp_path = REMOVED_ROLES_FILE + ".tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, REMOVED_ROLES_FILE)


def _save_removed_role(slug, inst_conf):
    data = _load_removed_roles()
    data[slug] = {
        "database": inst_conf.get("database"),
        "db_user": inst_conf["db_user"],
        "db_password": inst_conf["db_password"],
    }
    _store_removed_roles(data)


def _pop_removed_role(slug):
    data = _load_removed_roles()
    if data.pop(slug, None) is not None:
        _store_removed_roles(data)


# ----------------------------------------------------------------------
# Docker
# ----------------------------------------------------------------------


def _is_running(container):
    result = _run(["docker", "inspect", "-f", "{{.State.Running}}", container], timeout=30)
    return result["ok"] and result["output"].strip() == "true"


def provision_role(slug, recreate=True):
    """'./odoo provision-role <slug>': creates the instance's dedicated
    Postgres role if missing, gives it ownership of the databases matching
    its db_filter and closes CONNECT to PUBLIC.

    No Postgres role is a superuser, so the CLI briefly lets the bootstrap
    role log in, which RESTARTS the db-<service> container: every instance
    on that service loses its connection for a moment. Afterwards (with
    recreate) the configs are regenerated and the instance container, if
    running, is recreated so it connects with its own role.
    """
    config = _read_config()
    inst_conf = _get_instance(slug, config)
    db_user, db_password = inst_conf.get("db_user"), str(inst_conf.get("db_password") or "")
    if not db_user or not db_password:
        raise AgentError(f"'{slug}' no tiene db_user/db_password: defínelos antes de aprovisionar")
    # The CLI builds its SQL from these values: same rules as on upsert,
    # also for anything written to instances.json by hand
    _check(DB_ROLE_RE, db_user, "db_user")
    if not DB_PASSWORD_RE.match(db_password):
        raise AgentError("db_password de la instancia no es apto para aprovisionar (letras, dígitos, '_', '.', '-')")
    # Its databases: a specific db_filter or, without one, the single
    # database of db_name (same rule as './odoo provision-role')
    kind, db_scope = resolve_instance_db_scope(resolve_instance_config(inst_conf, config))
    if kind is None or "'" in db_scope or "\n" in db_scope or (kind == "filter" and "%" in db_scope):
        raise AgentError(
            f"'{slug}' necesita un db_filter específico (sin %h/%d ni comillas) o un "
            "db_name de una sola base para aprovisionar")

    if not _provision_lock.acquire(blocking=False):
        raise AgentError("Ya hay un aprovisionamiento en curso, intenta más tarde", 409)
    try:
        # the CLI asks for confirmation before the maintenance window
        result = _run([sys.executable, CLI_PATH, "provision-role", slug],
                      input="y\n", timeout=900, redact=(db_password,))
    finally:
        _provision_lock.release()
    result["db_service_restarted"] = f"db-{inst_conf['database']}"
    if not result["ok"] or not recreate:
        return result

    with _config_lock:
        _regen_configs(_read_config())
    service = f"odoo-{slug}"
    if _is_running(service):
        return {**_merge_results(result, _compose("up", "-d", "--no-deps", service)),
                "db_service_restarted": result["db_service_restarted"]}
    return result



def build(no_cache=False):
    if not _build_lock.acquire(blocking=False):
        raise AgentError("Ya hay un build en curso, intenta más tarde", 409)
    try:
        cmd = [sys.executable, CLI_PATH, "build"]
        if no_cache:
            cmd.append("--no-cache")
        return _run(cmd, timeout=3600)
    finally:
        _build_lock.release()


def start_instance(slug):
    _get_instance(slug)
    service = f"odoo-{slug}"
    # --no-deps: scoped to this instance, never touches the shared db
    result = _compose("up", "-d", "--no-deps", service)
    if not result["ok"]:
        return result
    return _merge_results(
        result,
        _run(["docker", "exec", "-u", "root", service, "chown", "-R", "odoo:odoo", "/home/odoo/data"]),
        # nginx only gets recreated if its published ports changed
        _compose("up", "-d", "nginx"),
    )


def stop_instance(slug):
    _get_instance(slug)
    return _compose("stop", f"odoo-{slug}")


def restart_instance(slug):
    _get_instance(slug)
    return _compose("restart", "--no-deps", f"odoo-{slug}")


def instances_status():
    """State of every odoo-<slug> container in one docker call."""
    config = _read_config()
    result = _run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.State}}"], timeout=30)
    if not result["ok"]:
        raise AgentError(f"No se pudo consultar Docker: {result['output']}", 502)
    states = dict(
        line.split("\t", 1) for line in result["output"].splitlines() if "\t" in line
    )
    return {
        slug: states.get(f"odoo-{slug}", "missing")
        for slug in config.get("instances", {})
    }


def update_modules(slug, modules, database, i18n_overwrite=False):
    _get_instance(slug)
    if not modules:
        raise AgentError("Debe indicar al menos un módulo")
    for module in modules:
        _check(MODULE_RE, module, "Módulo")
    _check(DBNAME_RE, database, "Base de datos")
    cmd = [
        "docker", "exec", "-u", "root", f"odoo-{slug}", "odoo",
        "--stop-after-init", "-p", "90", "--workers=0",
        "-u", ",".join(modules), "-d", database,
    ]
    if i18n_overwrite:
        cmd.append("--i18n-overwrite")
    return _run(cmd, timeout=3600)


def _psql(database_key, sql, config=None, user=None, password=None):
    """Run `sql` on a databases[] server as its service user (or as
    `user`/`password`, e.g. an instance's dedicated role); returns the
    agent result (output = psql -tA rows)."""
    _check(KEY_RE, database_key, "Base de datos")
    config = config or _read_config()
    db_conf = config.get("databases", {}).get(database_key)
    if not db_conf:
        raise AgentError(f"La base de datos '{database_key}' no existe en databases", 404)
    if user is None:
        user, password = db_conf["user"], db_conf.get("password")
    password = str(password or "")
    if db_conf.get("create_container", True):
        container, host, port = f"db-{database_key}", "localhost", 5432
    else:
        # External server: run psql from any instance container that uses it
        users = [
            slug for slug, conf in config.get("instances", {}).items()
            if conf.get("database") == database_key
        ]
        if not users:
            raise AgentError(f"Ninguna instancia usa la base de datos '{database_key}'", 404)
        container, host, port = f"odoo-{users[0]}", db_conf["host"], db_conf.get("port", 5432)
    return _run(
        ["docker", "exec", "-e", "PGPASSWORD", container, "psql",
         "-h", str(host), "-p", str(port), "-U", str(user),
         "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-tAc", sql],
        timeout=300, redact=(password,),
        env=dict(os.environ, PGPASSWORD=password),
    )


def list_databases(database_key):
    """Real databases (non-template, not 'postgres') on a databases[] server."""
    result = _psql(database_key, (
        "SELECT datname FROM pg_database WHERE datistemplate = false "
        "AND datname <> 'postgres' ORDER BY datname;"
    ))
    if not result["ok"]:
        raise AgentError(f"No se pudieron listar las bases: {result['output']}", 502)
    return {"databases": [line.strip() for line in result["output"].splitlines() if line.strip()]}


def _db_filter_matches(db_filter, dbname):
    try:
        return bool(db_filter) and re.match(db_filter, dbname) is not None
    except re.error:
        return False


# Named volumes compose_generator declares for every instance
INSTANCE_VOLUME_SUFFIXES = ("web", "data", "py3", "py")


def _compose_project():
    """Name of the compose project (volume names are prefixed with it)."""
    try:
        out = subprocess.run(
            ["docker", "compose", "-f", COMPOSE_FILE, "config", "--format", "json"],
            cwd=BASE_PATH, capture_output=True, text=True, timeout=60,
        ).stdout
        return json.loads(out).get("name", "")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ""


def purge_instance(slug, database_key, db_filter):
    """Delete what an instance leaves behind once removed: the databases
    matching its db_filter, its filestore volume (<slug>-web) and
    src/custom/<slug>/.

    Only for an instance that is no longer in instances.json (delete it
    first): if the slug is still there, the folder belongs to a live
    instance and nothing is touched. A database that also matches another
    instance's db_filter on the same server is kept."""
    _check(SLUG_RE, slug, "Instancia")
    db_filter = (db_filter or "").strip()
    if not db_filter.startswith("^") or len(db_filter) < 3 or "%" in db_filter:
        raise AgentError(
            "db_filter inválido para purgar: debe empezar por '^' y no usar %h/%d "
            f"(recibido: {db_filter!r})")
    try:
        re.compile(db_filter)
    except re.error as e:
        raise AgentError(f"db_filter no es una expresión regular válida: {e}")

    config = _read_config()
    instances = config.get("instances", {})
    if slug in instances:
        raise AgentError(
            f"'{slug}' sigue en instances.json: elimínala antes de purgar", 409)

    # Databases of an instance with its own role belong to that role: only
    # it (not the shared service user) can drop them
    role = _load_removed_roles().get(slug)
    if role and role.get("database") != database_key:
        role = None
    role_user = role["db_user"] if role else None
    role_password = role["db_password"] if role else None

    results, dropped, kept, failed = [], [], [], []
    for dbname in list_databases(database_key)["databases"]:
        if not _db_filter_matches(db_filter, dbname):
            continue
        shared_with = [
            other for other, conf in instances.items()
            if conf.get("database") == database_key and _db_filter_matches(
                conf.get("overwrite_odoo_config", {}).get("db_filter"), dbname)
        ]
        if shared_with or not DBNAME_RE.match(dbname):
            kept.append(dbname)
            continue
        result = _psql(database_key, f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE);', config,
                       user=role_user, password=role_password)
        results.append(result)
        (dropped if result["ok"] else kept).append(dbname)
        if not result["ok"]:
            failed.append(dbname)

    # Named volumes of the instance (filestore, data, python packages),
    # scoped to this compose project
    project = _compose_project()
    removed_volumes = []
    if project:
        for suffix in INSTANCE_VOLUME_SUFFIXES:
            volumes = _run(
                ["docker", "volume", "ls", "-q",
                 "--filter", f"label=com.docker.compose.project={project}",
                 "--filter", f"label=com.docker.compose.volume={slug}-{suffix}"],
                timeout=30,
            )
            for volume in volumes["output"].split():
                result = _run(["docker", "volume", "rm", volume], timeout=60)
                results.append(result)
                if result["ok"]:
                    removed_volumes.append(volume)

    instance_root = _repo_path(slug, ".")
    removed_dir = False
    if os.path.isdir(instance_root) and not os.path.islink(instance_root):
        try:
            shutil.rmtree(instance_root)
            removed_dir = True
        except OSError as e:
            results.append({
                "ok": False, "returncode": 1, "command": f"rm -rf {instance_root}",
                "output": f"[ERROR] No se pudo eliminar la carpeta: {e}",
            })

    merged = _merge_results(*results) if results else {
        "ok": True, "returncode": 0, "command": "", "output": ""}
    merged["output"] += (
        f"\n[INFO] Bases eliminadas: {', '.join(dropped) or '-'}"
        f"\n[INFO] Bases conservadas: {', '.join(kept) or '-'}"
        f"\n[INFO] Volúmenes eliminados: {', '.join(removed_volumes) or '-'}"
        f"\n[INFO] Carpeta {instance_root}: {'eliminada' if removed_dir else ('no existía' if not os.path.exists(instance_root) else 'NO se pudo eliminar')}"
    )
    if role:
        merged["output"] += (
            f"\n[INFO] El rol '{role_user}' sigue en Postgres: borrarlo requiere superusuario "
            "(DROP ROLE con el rol bootstrap)")
        if not failed:
            _pop_removed_role(slug)
    merged.update({
        "dropped_databases": dropped, "kept_databases": kept,
        "removed_volumes": removed_volumes, "removed_dir": removed_dir,
    })
    return merged


# ----------------------------------------------------------------------
# Git repositories
# ----------------------------------------------------------------------
# Two layouts are supported, and can be mixed:
#   - src/custom/<slug>/<repo>/   one repo per subfolder (dir = "<repo>")
#   - src/custom/<slug>/          the instance folder IS the repo (dir = "."),
#                                 usually with submodules in subfolders
# Submodules count as repos too (their .git is a file, not a folder).


def _clean_url(url):
    """Remote URL without embedded credentials (https://TOKEN@github.com/...)."""
    return CREDENTIALS_IN_URL_RE.sub(r"\1", url or "")


def _is_repo(path):
    return os.path.exists(os.path.join(path, ".git"))


def _repos_inside(path):
    """Names of the direct subfolders of `path` that are git repos."""
    if not os.path.isdir(path):
        return []
    return sorted(
        name for name in os.listdir(path)
        if not name.startswith(".") and _is_repo(os.path.join(path, name))
    )


def _git(repo_path, *args, timeout=60, redact=(), env=None):
    # The checkout may belong to another user (e.g. bpadm): trust it explicitly
    return _run(
        ["git", "-c", f"safe.directory={repo_path}", "-C", repo_path, *args],
        timeout=timeout, redact=redact, env=env,
    )


def _git_out(repo_path, *args):
    result = _git(repo_path, *args, timeout=15)
    return result["output"].strip() if result["ok"] else ""


def _list_modules(path):
    if not os.path.isdir(path):
        return []
    return sorted(
        entry for entry in os.listdir(path)
        if os.path.isfile(os.path.join(path, entry, "__manifest__.py"))
    )


def _changed_modules(repo_path, old_commit, new_commit):
    """Modules (top-level folders with a manifest) touched between two commits."""
    if not old_commit or not new_commit or old_commit == new_commit:
        return []
    names = _git_out(repo_path, "diff", "--name-only", old_commit, new_commit)
    folders = {name.split("/", 1)[0] for name in names.splitlines() if "/" in name}
    return sorted(
        folder for folder in folders
        if os.path.isfile(os.path.join(repo_path, folder, "__manifest__.py"))
    )


def _repo_path(slug, repo_dir):
    _check(SLUG_RE, slug, "Instancia")
    if repo_dir != ".":
        _check(REPO_DIR_RE, repo_dir, "Directorio del repositorio")
    instance_root = os.path.join(CUSTOM_ADDONS_ROOT, slug)
    return instance_root if repo_dir == "." else os.path.join(instance_root, repo_dir)


def _repo_info(repo_dir, repo_path):
    return {
        "dir": repo_dir,
        "remote_url": _clean_url(_git_out(repo_path, "remote", "get-url", "origin")),
        "branch": _git_out(repo_path, "branch", "--show-current"),
        "commit": _git_out(repo_path, "rev-parse", "--short", "HEAD"),
        "submodule": os.path.isfile(os.path.join(repo_path, ".git")),
        "modules": _list_modules(repo_path),
    }


def list_repos(slug):
    _get_instance(slug)
    instance_root = os.path.join(CUSTOM_ADDONS_ROOT, slug)
    repos = []
    if os.path.isdir(instance_root):
        if _is_repo(instance_root):
            repos.append(_repo_info(".", instance_root))
        for entry in sorted(os.listdir(instance_root)):
            repo_path = os.path.join(instance_root, entry)
            if os.path.isdir(repo_path) and _is_repo(repo_path):
                repos.append(_repo_info(entry, repo_path))
    return {"repos": repos}


def _token_env(token):
    """Environment for a git command that sends every github.com remote (SSH
    or HTTPS) through HTTPS with the token, so the repo and its submodules
    authenticate the same way. It goes in GIT_CONFIG_* variables and not in
    the arguments, so it never shows up in `ps`; nothing is stored in
    .git/config. None without a token."""
    if not token:
        return None
    base = f"https://x-access-token:{token}@github.com/"
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": f"url.{base}.insteadOf", "GIT_CONFIG_VALUE_0": "git@github.com:",
        "GIT_CONFIG_KEY_1": f"url.{base}.insteadOf", "GIT_CONFIG_VALUE_1": "https://github.com/",
    })
    return env


def clone_repo(slug, url, branch, repo_dir, token=None):
    """git clone -b <branch> (with its submodules) into
    src/custom/<slug>/<repo_dir>, creating the instance folder if needed.
    If the folder already exists nothing is cloned; `branch_mismatch` tells
    whether its checkout is on another branch."""
    _get_instance(slug)
    _check(REPO_URL_RE, url, "URL del repositorio")
    _check(BRANCH_RE, branch, "Rama")
    if repo_dir == ".":
        raise AgentError("No se puede clonar sobre la carpeta de la instancia; indica un subdirectorio")
    repo_path = _repo_path(slug, repo_dir)
    if os.path.exists(repo_path):
        current = _git_out(repo_path, "branch", "--show-current") if _is_repo(repo_path) else ""
        mismatch = current != branch
        output = f"[INFO] {repo_path} ya existe, no se clona"
        if mismatch:
            output += (
                f"\n[WARNING] Está en la rama '{current}', no en '{branch}'"
                if current else f"\n[WARNING] No es un repositorio git o no está en ninguna rama"
            )
        return {
            "ok": True, "returncode": 0, "command": "", "cloned": False,
            "output": output, "branch": current, "branch_mismatch": mismatch,
            "modules": _list_modules(repo_path),
        }
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    result = _run(
        ["git", "clone", "--recurse-submodules", "-b", branch, "--", url, repo_path],
        timeout=1800, redact=(token,), env=_token_env(token),
    )
    if not result["ok"] and os.path.isdir(repo_path):
        # Don't leave a half-cloned folder: the next clone would skip it as
        # "already exists". It didn't exist before this call.
        shutil.rmtree(repo_path, ignore_errors=True)
        result["output"] += f"\n[INFO] Clonado incompleto: se eliminó {repo_path}"
    result.update({
        "cloned": result["ok"], "branch": branch if result["ok"] else "",
        "branch_mismatch": False, "modules": _list_modules(repo_path),
    })
    return result


def _server_repo_path(path):
    """Absolute path of a repo given relative to the docker-odoo root, as
    the user types it (e.g. "/src/custom/bp-staging"). It must stay inside
    src/: no "..", and symlinks can't take it out of there either."""
    rel = (path or "").strip().strip("/")
    _check(SERVER_PATH_RE, rel, "Ruta del repositorio")
    if ".." in rel.split("/"):
        raise AgentError("La ruta del repositorio no puede contener '..'")
    src_root = os.path.realpath(os.path.join(BASE_PATH, "src"))
    repo_path = os.path.realpath(os.path.join(BASE_PATH, rel))
    if os.path.commonpath([src_root, repo_path]) != src_root:
        raise AgentError("La ruta del repositorio debe estar dentro de src/ de docker-odoo")
    return repo_path


def pull_repo(slug, repo_dir, branch, url=None, token=None, update_submodules=False):
    """pull_repo_at for src/custom/<slug>/<repo_dir> ("." = the instance folder)."""
    _get_instance(slug)
    return pull_repo_at(_repo_path(slug, repo_dir), branch, url, token, update_submodules)


def pull_repo_at_server_path(path, branch, url=None, token=None, update_submodules=False):
    """pull_repo_at for a path relative to the docker-odoo root."""
    return pull_repo_at(_server_repo_path(path), branch, url, token, update_submodules)


def pull_repo_at(repo_path, branch, url=None, token=None, update_submodules=False):
    """Bring the repo to the latest commit of `branch`, never merging.

    fetch + switch to `branch` (created from the fetched commit if it doesn't
    exist locally) + fast-forward only. If the local branch has diverged or
    local changes are in the way, nothing is changed and the error is
    returned. The response includes which modules changed, so only those
    need `-u`.
    """
    _check(BRANCH_RE, branch, "Rama")
    if not _is_repo(repo_path):
        msg = f"{repo_path} no existe o no es un repositorio git"
        inner = _repos_inside(repo_path)
        if inner:
            msg += f". Contiene los repositorios: {', '.join(inner)}; indica la ruta de uno de ellos"
        raise AgentError(msg, 404)
    source, env = "origin", _token_env(token)
    if url:
        _check(REPO_URL_RE, url, "URL del repositorio")
        if env and GITHUB_PATH_RE.match(url):
            # fetch from the URL itself: _token_env turns it into HTTPS + token
            source = url

    old_commit = _git_out(repo_path, "rev-parse", "HEAD")
    old_branch = _git_out(repo_path, "branch", "--show-current")
    steps = [_git(repo_path, "fetch", source, branch, timeout=600, redact=(token,), env=env)]
    if steps[-1]["ok"] and old_branch != branch:
        has_local = _git(repo_path, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", timeout=10)["ok"]
        if has_local:
            steps.append(_git(repo_path, "checkout", branch))
        else:
            steps.append(_git(repo_path, "checkout", "-b", branch, "FETCH_HEAD"))
    if steps[-1]["ok"]:
        steps.append(_git(repo_path, "merge", "--ff-only", "FETCH_HEAD", timeout=300))
    if steps[-1]["ok"] and update_submodules:
        steps.append(_git(
            repo_path, "submodule", "update", "--init", "--recursive",
            timeout=900, redact=(token,), env=env,
        ))

    result = _merge_results(*steps)
    new_commit = _git_out(repo_path, "rev-parse", "HEAD")
    result.update({
        "path": repo_path,
        "branch": _git_out(repo_path, "branch", "--show-current"),
        "old_commit": old_commit[:12],
        "new_commit": new_commit[:12],
        "updated": bool(old_commit and new_commit and old_commit != new_commit),
        "changed_modules": _changed_modules(repo_path, old_commit, new_commit),
        "modules": _list_modules(repo_path),
    })
    return result
