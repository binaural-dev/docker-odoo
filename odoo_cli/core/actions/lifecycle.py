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

import json
import subprocess
import sys
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


def build_odoo(
    runner: "Runner", config: dict, no_cache: bool, no_confirm: bool = False
) -> None:
    """Generate all config files and build Docker images.

    ``no_confirm`` only affects step 3.5 (the ``db_filter`` drift audit):
    it skips the interactive offer to auto-correct the fixable findings,
    so a non-interactive build (CI/automation) never hangs on a prompt and
    never changes Postgres ownership without explicit confirmation. The
    audit itself always runs and only ever warns — it must never block
    the build.
    """
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

    # 3.5 Audit db_filter vs the real ownership/CONNECT state in Postgres.
    #     Editing db_filter in instances.json re-triggers no ownership
    #     change on its own, so this read-only audit is the only thing
    #     that catches the resulting drift. It warns (never blocks) and
    #     offers to auto-fix only the unambiguous findings.
    from odoo_cli.core.actions.postgres import (
        audit_db_filter_drift,
        maybe_fix_drift,
        print_db_filter_audit,
    )

    findings = audit_db_filter_drift(config)
    print_db_filter_audit(runner, findings)
    maybe_fix_drift(runner, config, findings, no_confirm)

    # 4. Build images
    runner.info("\n=== Construyendo imágenes Docker ===\n")
    if no_cache:
        returncode = _docker_compose(runner, "build", "--no-cache")
    else:
        returncode = _docker_compose(runner, "build")

    # compose builds in parallel and cancels the rest when one image fails:
    # without this the output ended in "Build completado" anyway, and the
    # agent (micro_saas) reported the build as successful
    if returncode != 0:
        runner.error(
            f"\n❌ Build fallido: 'docker compose build' terminó con código {returncode}. "
            f"Revisa el primer 'failed to solve' de arriba.\n"
        )
        sys.exit(returncode)

    runner.info("\n✅ Build completado.\n")
    _warn_legacy_lib_volumes(runner)


# Volumes that older checkouts mounted over /usr/local/lib and /usr/lib.
LEGACY_LIB_VOLUME_SUFFIXES = ("-py3", "-py")


def _legacy_lib_volumes() -> dict[str, list[str]]:
    """Leftover ``<instance>-py3`` / ``<instance>-py`` volumes of this
    Compose project, grouped by instance. Matched by Compose's own label,
    never by volume name."""
    result = subprocess.run(
        [
            "docker", "volume", "ls",
            "--filter", f"label=com.docker.compose.project={_compose_project()}",
            "--format", '{{.Name}} {{.Label "com.docker.compose.volume"}}',
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {}
    found: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        name, _sep, declared = line.strip().partition(" ")
        for suffix in LEGACY_LIB_VOLUME_SUFFIXES:
            if declared.endswith(suffix):
                found.setdefault(declared[: -len(suffix)], []).append(name)
                break
    return found


def _warn_legacy_lib_volumes(runner: "Runner") -> None:
    """After a build, point at the volumes that still freeze old code.

    They are not removed here: a container created before this change still
    mounts them, and only the user knows when an instance can be recreated.
    """
    legacy = _legacy_lib_volumes()
    if not legacy:
        return
    lines = []
    for instance in sorted(legacy):
        lines.append(
            f"  docker compose -f {COMPOSE_FILE} up -d --force-recreate odoo-{instance}"
        )
        lines.append(f"  docker volume rm {' '.join(sorted(legacy[instance]))}")
    runner.warn(
        "\n⚠️  Estas instancias todavía tienen volúmenes sobre /usr/lib y "
        "/usr/local/lib: mientras existan, siguen corriendo el Odoo y las "
        "librerías de la imagen con la que se crearon, no las de este build. "
        "Recrea cada instancia y borra sus volúmenes (o usa './odoo remove "
        "<instancia> --full', que también los borra):\n" + "\n".join(lines)
    )


# ============================================================
# Start / Stop / Restart
# ============================================================


def start_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Start database(s), Odoo instance(s), and nginx."""
    if instance:
        runner.info(f"\n=== ▶️  INICIANDO INSTANCIA: {instance.upper()} ===\n")
    else:
        runner.info("\n=== ▶️  INICIANDO TODAS LAS INSTANCIAS ===\n")

    from odoo_cli.core.actions.validate import check_host_port_collisions

    check_host_port_collisions(runner, config, compose_file=COMPOSE_FILE)

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
                    "docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "-u", "root", svc,
                    "chown", "-R", "odoo:odoo", "/home/odoo/data",
                ],
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # Start nginx. Force-recreate it so the bind-mounted nginx config
    # (which may have just changed) is actually picked up — nginx only
    # reads its config at container start. Targets the compose *service*
    # (not a fixed container name: nginx's real container name is
    # namespaced by the Compose project, not a bare "odoo-nginx").
    runner.info("\n→ Iniciando Nginx...")
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "rm", "-s", "-f", "nginx"],
        stderr=subprocess.DEVNULL,
    )
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


REMOVE_FULL = "full"
REMOVE_DBS = "dbs"
REMOVE_CANCEL = "cancel"

# Named volumes of an instance service, as the compose generator declares
# them (``<instance>-<suffix>``). ``py3``/``py`` are no longer generated but
# may still exist on checkouts created before that change, so they are
# cleaned up too.
INSTANCE_VOLUME_SUFFIXES = ("web", "data", "py3", "py")


def _compose_project() -> str:
    """Name of the Compose project, which prefixes every volume it creates.

    Asked to Compose itself rather than derived from the directory, so a
    ``COMPOSE_PROJECT_NAME`` or a renamed checkout is respected. Falls back
    to the directory slug the generator uses for image names.
    """
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "config", "--format", "json"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)["name"]
        except (ValueError, KeyError):
            pass
    from generators.compose_generator import _project_slug

    return _project_slug(".")


def _project_volumes(project: str, volume: str | None = None) -> list[str]:
    """Real names of the volumes Compose created for ``project``, optionally
    only the one declared as ``volume`` in the compose file. Matched by the
    labels Compose puts on them, never by name prefix."""
    argv = [
        "docker", "volume", "ls", "-q",
        "--filter", f"label=com.docker.compose.project={project}",
    ]
    if volume:
        argv += ["--filter", f"label=com.docker.compose.volume={volume}"]
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [name.strip() for name in result.stdout.splitlines() if name.strip()]


def _instance_image(config: dict, instance: str) -> str:
    """Image tag of an instance, as the compose generator names it."""
    from generators.compose_generator import _project_slug
    from generators.config_loader import get_odoo_minor

    odoo_minor = get_odoo_minor(config["instances"][instance]["odoo_version"])
    return f"local_odoo_{_project_slug('.')}_{instance}:{odoo_minor}"


def _image_exists(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, text=True
    )
    return result.returncode == 0


def _offer_restart(runner: "Runner", config: dict, instance: str | None) -> None:
    # Default No: an extra Enter must not bring back what was just removed.
    if runner.confirm("¿Deseas levantar el entorno nuevamente en blanco?", default=False):
        start_odoo(runner, config, instance)


def remove_odoo(
    runner: "Runner", config: dict, instance: str | None, mode: str | None = None
) -> None:
    """Remove an instance (completely, or only some of its databases), or
    the whole environment when ``instance`` is None.

    With an instance, ``mode`` picks what to remove (``REMOVE_FULL`` or
    ``REMOVE_DBS``); without it the user is asked. The whole environment
    is confirmed by typing the Compose project name.

    Hard-blocked (no confirm, no override) against any instance flagged
    ``"production": true`` in instances.json — this is the only lifecycle
    action that deletes volumes (real data loss), so it's the one that
    gets a real gate instead of just a confirmation prompt. To remove a
    production instance for real, the flag has to be edited out of
    instances.json by hand first.
    """
    from generators.config_loader import is_production_instance

    if instance:
        if is_production_instance(config["instances"][instance]):
            runner.error(
                f"\n⛔ '{instance}' está marcada como \"production\": true. "
                "'./odoo remove' está bloqueado para instancias de producción "
                "(sacá el flag a mano en instances.json si de verdad necesitás correrlo)."
            )
            sys.exit(1)
    else:
        prod_instances = sorted(
            n for n, c in config["instances"].items() if is_production_instance(c)
        )
        if prod_instances:
            runner.error(
                f"\n⛔ Bloqueado: hay instancia(s) de producción en la configuración "
                f"({', '.join(prod_instances)}). './odoo remove' sin instancia "
                "específica no puede ejecutarse mientras existan instancias de producción."
            )
            sys.exit(1)

    if not instance:
        _remove_environment(runner, config)
        return

    if mode is None:
        mode = runner.select_one(
            f"¿Qué deseas eliminar de la instancia '{instance}'?",
            [
                ("Instancia completa: contenedor, volúmenes, imagen y bases de datos", REMOVE_FULL),
                ("Solo bases de datos de la instancia", REMOVE_DBS),
                ("Cancelar", REMOVE_CANCEL),
            ],
        )
    if mode == REMOVE_DBS:
        from odoo_cli.core.actions.postgres import psql_remove_database

        psql_remove_database(runner, config, instance, None, use_ps=False)
    elif mode == REMOVE_FULL:
        _remove_instance(runner, config, instance)
    else:
        runner.info("\nOperación cancelada.")


def _remove_instance(runner: "Runner", config: dict, instance: str) -> None:
    """Remove an instance completely: its container, named volumes, image
    and every database its ``db_filter`` matches.

    The databases are dropped first, with the instance stopped so no
    session is left open; if one fails nothing else is removed, so the
    command can simply be run again.
    """
    from generators.config_loader import (
        get_db_host,
        get_db_internal_port,
        resolve_db_config,
        resolve_instance_config,
        resolve_instance_db_creds,
    )
    from odoo_cli.core.actions.postgres import _drop_database
    from odoo_cli.core.instance import has_own_db_filter, list_instance_databases

    inst_conf = config["instances"][instance]
    db_filter = resolve_instance_config(inst_conf, config).get("db_filter")
    if not has_own_db_filter(db_filter):
        # Without its own filter the listing would include the databases
        # of every other instance on the same Postgres service.
        runner.error(
            f"\n⛔ '{instance}' no tiene un db_filter propio (o es '*'): no se "
            "puede saber cuáles bases son suyas sin arrastrar las de otras "
            "instancias del mismo Postgres. Define su db_filter en instances.json, "
            f"o borra sus bases a mano con './odoo remove {instance} --dbs'."
        )
        sys.exit(1)

    databases = list_instance_databases(config, instance)
    if databases is None:
        runner.error(
            f"\n❌ No se pudieron listar las bases de '{instance}' (¿está "
            f"levantado el Postgres '{inst_conf['database']}'?). No se eliminó nada."
        )
        sys.exit(1)

    service = f"odoo-{instance}"
    project = _compose_project()
    volumes = [
        name
        for suffix in INSTANCE_VOLUME_SUFFIXES
        for name in _project_volumes(project, f"{instance}-{suffix}")
    ]
    image = _instance_image(config, instance)
    has_image = _image_exists(image)

    listing = [f"  - Contenedor: {service}"]
    listing += [f"  - Volumen: {name}" for name in volumes] or ["  - Volúmenes: ninguno"]
    listing.append(f"  - Imagen: {image}" if has_image else "  - Imagen: no existe")
    listing += [f"  - Base de datos: {name}" for name in databases] or [
        "  - Bases de datos: ninguna"
    ]
    runner.warn(
        f"\n⚠️  \033[1mPELIGRO\033[0m: se eliminará la instancia "
        f"'\033[91m{instance}\033[0m' completa:\n" + "\n".join(listing) + "\n"
        "Las bases de otras instancias no se tocan. Esto NO se puede deshacer."
    )
    typed = runner.prompt_text(
        f"Escribe el nombre de la instancia ('{instance}') para confirmar"
    )
    if (typed or "").strip() != instance:
        runner.info("\nOperación cancelada.")
        return

    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "stop", service], stdin=subprocess.DEVNULL)

    if databases:
        db_conf = resolve_db_config(inst_conf, config)
        db_user, db_password = resolve_instance_db_creds(inst_conf, db_conf)
        if db_conf.get("create_container", True):
            # Straight into the Postgres service: the instance is stopped.
            target, host_args = get_db_host(inst_conf["database"], db_conf), []
        else:
            # An external Postgres is only reachable through the instance.
            subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "start", service], stdin=subprocess.DEVNULL)
            target = service
            host_args = [
                "-h", get_db_host(inst_conf["database"], db_conf),
                "-p", str(get_db_internal_port(db_conf)),
            ]
        for dbname in databases:
            runner.info(f"\n→ Eliminando base de datos '{dbname}'...")
            if not _drop_database(runner, target, db_user, db_password, dbname, host_args):
                runner.error(
                    f"❌ No se pudo eliminar '{dbname}'. Se detuvo antes de borrar "
                    "el contenedor, los volúmenes y la imagen: corrige y vuelve a "
                    "correr el comando."
                )
                sys.exit(1)
            runner.info(f"✅ Base de datos '{dbname}' eliminada.")

    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "rm", "-s", "-f", service],
        stdin=subprocess.DEVNULL,
    )
    if volumes:
        subprocess.run(["docker", "volume", "rm", *volumes])
    if has_image:
        subprocess.run(["docker", "image", "rm", image])

    runner.info(f"\n🛑 Instancia '{instance}' eliminada.\n")
    _offer_restart(runner, config, instance)


def _remove_environment(runner: "Runner", config: dict) -> None:
    """Remove every container and volume of the Compose project — the
    Postgres ones included, that is, the databases of all instances.
    Confirmed by typing the project name, not with a yes/no."""
    project = _compose_project()
    volumes = _project_volumes(project)
    pg_volumes = {
        name
        for db_name in config.get("databases", {})
        for name in _project_volumes(project, f"{db_name}-data")
    }
    listing = "\n".join(
        f"  - {name}" + ("  ← Postgres: TODAS sus bases de datos" if name in pg_volumes else "")
        for name in volumes
    ) or "  (no hay volúmenes creados)"
    runner.warn(
        f"\n⚠️  \033[1mPELIGRO\033[0m: esto eliminará \033[91mTODAS\033[0m las "
        f"instancias del proyecto '{project}' y estos volúmenes:\n{listing}\n"
        "Esto NO se puede deshacer."
    )
    typed = runner.prompt_text(
        f"Escribe el nombre del proyecto ('{project}') para confirmar"
    )
    if (typed or "").strip() != project:
        runner.info("\nOperación cancelada.")
        return

    _docker_compose(runner, "down", "-v", "--remove-orphans")
    runner.info("\n🛑 Eliminado.\n")
    _offer_restart(runner, config, None)


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
                    "docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "-u", "root", svc,
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
