"""Postgres role isolation: per-instance dedicated roles + drift audit.

Why this module exists
----------------------
Odoo's internal cron (``ir.cron``) does NOT respect ``dbfilter`` —
``dbfilter`` is purely an HTTP routing mechanism, never consulted by
the cron dispatcher. When several instances share one Postgres service
(``databases.<name>`` in ``instances.json``), the cron of instance A
happily runs scheduled actions on instance B's databases. That caused a
real incident (see
``openspec/changes/2026-08-17-per-instance-postgres-roles-cron-isolation``).

The fix is at the Postgres level, not in Odoo's code: give each
instance its own role, owner of only the databases matching its
``db_filter``. Odoo's native ``list_dbs()`` already filters by
``datdba = current_user``, so that native filter is enough — nothing to
patch. ``REVOKE CONNECT ... FROM PUBLIC`` is the second layer, which
also covers the threaded mode (that one never even calls
``list_dbs()``, it iterates already-loaded registries).

Two entry points
----------------
* :func:`provision_instance_role` — ``./odoo provision-role <instance>``,
  one instance end to end (own break-glass window).
* :func:`audit_db_filter_drift` / :func:`print_db_filter_audit` /
  :func:`maybe_fix_drift` — read-only audit run on every
  ``./odoo build``, because editing ``db_filter`` in ``instances.json``
  re-triggers nothing on its own. Only the two unambiguous drift
  categories are ever offered for auto-correction.

Break-glass
-----------
Creating/altering roles needs ``CREATEROLE``, which lives on the
cluster bootstrap role — and that role is kept ``NOLOGIN`` on purpose
(see ``openspec/specs/postgres-security/spec.md``). So provisioning
temporarily flips it to ``LOGIN`` via ``postgres --single`` (the only
way in once ``NOLOGIN``) and re-blocks it right after. That means a
brief maintenance window for the WHOLE Postgres service, which is why
the batch path groups targets by service: one window, not one per
instance.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

from odoo_cli.core.actions.lifecycle import COMPOSE_FILE


# Container resolution and the break-glass dance live in
# ``generators.db_bootstrap`` so this module and ``scripts/odoo_restore``
# (standalone, no Runner) can't drift apart. The wrappers below only add
# Runner-aware output on top.
from generators.db_bootstrap import (  # noqa: E402
    container_id as _container_id,
    bootstrap_needs_breakglass as _bootstrap_needs_breakglass,
    bootstrap_breakglass_enable as _bootstrap_breakglass_enable_impl,
)

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


# ============================================================
# Low-level psql plumbing
# ============================================================


def _pg_exec(
    runner: "Runner",
    db_container: str,
    pg_user: str,
    pg_password: str,
    dbname: str,
    sql: str,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run one SQL statement via ``docker exec``, as argv (not a shell string)
    so nested double-quoted Postgres identifiers can't collide with shell
    quoting."""
    result = subprocess.run(
        [
            "docker", "exec", "-e", f"PGPASSWORD={pg_password}", _container_id(db_container),
            "psql", "-U", pg_user, "-d", dbname, "-v", "ON_ERROR_STOP=1", "-c", sql,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if result.stdout:
            runner.info(result.stdout.rstrip())
        if result.stderr:
            runner.error(result.stderr.rstrip())
        if check:
            sys.exit(1)
    return result


def _fetch_database_ownership(
    db_container: str, user: str, password: str
) -> list[dict] | None:
    """Pure read: list every real (non-template) database of this Postgres
    service with its current owner and whether PUBLIC can still connect.

    Uses the regular service role (the one the Odoo containers already
    use) — no break-glass and no bootstrap role needed, because the
    name/owner of each database is catalog metadata, visible to any
    login role even without ``CONNECT`` on that particular database.

    Returns ``None`` when the service is unreachable, so the caller can
    tell "nothing to report" apart from "couldn't look".
    """
    try:
        container_id = _container_id(db_container)
    except RuntimeError:
        return None
    result = subprocess.run(
        ["docker", "exec", "-e", f"PGPASSWORD={password}", container_id,
         "psql", "-U", user, "-d", "postgres", "-tAc",
         "SELECT d.datname, r.rolname, has_database_privilege('public', d.datname, 'CONNECT') "
         "FROM pg_database d JOIN pg_roles r ON r.oid = d.datdba WHERE NOT d.datistemplate;"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        datname, owner, public_connect = line.split("|")
        rows.append({
            "datname": datname,
            "owner": owner,
            "public_connect": public_connect == "t",
        })
    return rows


# ============================================================
# Drift audit (read-only, runs on every build)
# ============================================================


def audit_db_filter_drift(config: dict) -> list[dict]:
    """Compare, for every Postgres service shared by >1 instance, each
    instance's resolved ``db_filter`` against the real ownership/CONNECT
    state in Postgres.

    Only reads, never modifies anything — returns a list of structured
    findings (dicts, not strings) so the caller can both print them and
    decide which ones ``provision-role`` can fix without ambiguity
    (see :func:`maybe_fix_drift`).

    Each finding carries ``category``, ``instance`` (or ``None`` when it
    involves more than one), ``message`` (already formatted for
    printing) and ``fixable`` (whether ``provision-role`` on
    ``instance`` resolves it unambiguously).

    Why this is needed: ``provision-role`` applies ownership/CONNECT
    once, when run by hand. Editing ``db_filter`` in ``instances.json``
    afterwards re-triggers nothing — this audit is what detects the
    resulting drift, so we can warn on every ``./odoo build`` instead of
    finding out through a real incident (which already happened once).
    """
    from generators.config_loader import resolve_instance_config

    by_service = defaultdict(list)
    for inst_name, inst_conf in config["instances"].items():
        by_service[inst_conf["database"]].append(inst_name)

    findings: list[dict] = []

    for db_name, inst_names in by_service.items():
        if len(inst_names) <= 1:
            continue  # una sola instancia en el servicio, sin riesgo de cruce

        db_conf = config["databases"][db_name]
        db_container = f"db-{db_name}"
        rows = _fetch_database_ownership(
            db_container, db_conf["user"], db_conf["password"]
        )
        if rows is None:
            findings.append({
                "category": "unreachable", "instance": None, "fixable": False,
                "message": (
                    f"[{db_name}] no se pudo leer el estado real de Postgres "
                    f"para auditar (servicio caido o inalcanzable?) -- omitido"
                ),
            })
            continue

        matches_by_db = defaultdict(list)

        for inst_name in inst_names:
            inst_conf = config["instances"][inst_name]
            odoo_conf = resolve_instance_config(inst_conf, config)
            db_filter = odoo_conf.get("db_filter") or ""
            max_cron_threads = odoo_conf.get("max_cron_threads", 1)
            expected_user = inst_conf.get("db_user")

            if not db_filter or db_filter == "*" or "%h" in db_filter or "%d" in db_filter:
                continue  # ya lo reporta _validate_cron_dbfilter_isolation, no duplicar

            try:
                matched = [r for r in rows if re.match(db_filter, r["datname"])]
            except re.error:
                continue  # regex invalido -- tampoco duplicar aca

            for r in matched:
                matches_by_db[r["datname"]].append(inst_name)

                if expected_user and r["owner"] != expected_user:
                    findings.append({
                        "category": "owner_mismatch", "instance": inst_name, "fixable": True,
                        "message": (
                            f"[{inst_name}] '{r['datname']}' matchea su db_filter "
                            f"('{db_filter}') pero pertenece al rol '{r['owner']}', no a "
                            f"'{expected_user}' -- correr: ./odoo provision-role {inst_name}"
                        ),
                    })
                elif (expected_user and max_cron_threads != 0
                        and r["owner"] == expected_user and r["public_connect"]):
                    findings.append({
                        "category": "connect_open", "instance": inst_name, "fixable": True,
                        "message": (
                            f"[{inst_name}] '{r['datname']}' ya es del rol correcto pero "
                            f"PUBLIC todavia puede conectarse (CONNECT no revocado) -- "
                            f"correr: ./odoo provision-role {inst_name}"
                        ),
                    })

            if expected_user:
                for r in rows:
                    if r["owner"] == expected_user and not re.match(db_filter, r["datname"]):
                        findings.append({
                            "category": "filter_drift", "instance": inst_name, "fixable": False,
                            "message": (
                                f"[{inst_name}] '{r['datname']}' pertenece a su rol dedicado "
                                f"'{expected_user}' pero YA NO matchea su db_filter actual "
                                f"('{db_filter}') -- el filtro cambio despues de aprovisionar; "
                                f"revisar si es intencional (¿la base deberia pasar a otra "
                                f"instancia?) o si el filtro se edito por error -- NO se "
                                f"ofrece correccion automatica, requiere revision manual"
                            ),
                        })

        for datname, matched_insts in matches_by_db.items():
            if len(matched_insts) > 1:
                findings.append({
                    "category": "overlap", "instance": None, "fixable": False,
                    "message": (
                        f"[{db_name}] '{datname}' matchea el db_filter de mas de una "
                        f"instancia a la vez ({', '.join(matched_insts)}) -- los regex se "
                        f"solapan, revisarlos antes de aprovisionar (aprovisionar de mas "
                        f"puede robarle la base a la instancia que ya la tenia) -- NO se "
                        f"ofrece correccion automatica, requiere revision manual"
                    ),
                })

    return findings


def print_db_filter_audit(runner: "Runner", findings: list[dict]) -> None:
    """Render the result of :func:`audit_db_filter_drift`.

    Unlike the config_loader validation (which aborts execution), this
    only warns — it must never block the build.
    """
    runner.info("\n=== 🔍 AUDITORÍA: db_filter vs ownership real en Postgres ===\n")
    if not findings:
        runner.info(
            "✅ Sin diferencias -- el db_filter de cada instancia coincide "
            "con el ownership/CONNECT real.\n"
        )
        return
    runner.warn(f"⚠️  {len(findings)} diferencia(s) encontrada(s):\n")
    for f in findings:
        runner.warn(f"  - {f['message']}")
    runner.info("")


# ============================================================
# Provisioning: target resolution + break-glass
# ============================================================


def _resolve_provision_target(runner: "Runner", config: dict, instance: str) -> dict:
    """Validate and resolve everything :func:`provision_role_sql` and the
    bootstrap helpers need for one instance. Exits on bad config."""
    from generators.config_loader import resolve_instance_config

    inst_conf = config["instances"].get(instance)
    if inst_conf is None:
        runner.error(f"Error: instancia '{instance}' no existe.")
        sys.exit(1)

    db_user = inst_conf.get("db_user")
    db_password = inst_conf.get("db_password")
    if not db_user or not db_password:
        runner.error(
            f"Error: la instancia '{instance}' no tiene 'db_user'/'db_password' "
            f"en instances.json (a nivel raiz de la instancia, no dentro de "
            f"overwrite_odoo_config). Agregalos antes de aprovisionar."
        )
        sys.exit(1)

    db_name = inst_conf["database"]
    db_conf = config["databases"][db_name]
    odoo_conf = resolve_instance_config(inst_conf, config)
    db_filter = odoo_conf.get("db_filter") or ""
    if not db_filter or db_filter == "*" or "%h" in db_filter or "%d" in db_filter:
        runner.error(
            f"Error: '{instance}' no tiene un db_filter especifico y estatico "
            f"(sin %h/%d) -- no se puede resolver de forma segura que bases le "
            f"pertenecen. Definilo antes de aprovisionar."
        )
        sys.exit(1)

    return {
        "instance": instance,
        "db_name": db_name,
        "db_container": f"db-{db_name}",
        "db_conf": db_conf,
        "bootstrap_user": db_conf.get("bootstrap_user", db_conf["user"]),
        "bootstrap_password": db_conf.get("bootstrap_password", db_conf["password"]),
        "db_user": db_user,
        "db_password": db_password,
        "db_filter": db_filter,
    }


def _bootstrap_breakglass_enable(
    runner: "Runner", db_container: str, bootstrap_user: str, db_conf: dict, db_name: str
) -> None:
    """Stop the db service, flip the bootstrap role to ``LOGIN`` via
    ``postgres --single`` (bypasses normal auth — the only way in once
    ``NOLOGIN``, since creating roles needs ``CREATEROLE``), then start it
    back up.

    The mechanics live in :func:`generators.db_bootstrap.bootstrap_breakglass_enable`
    (shared with ``scripts/odoo_restore``); this only binds this project's
    ``COMPOSE_FILE`` and keeps the Runner-shaped signature the callers use.
    """
    _bootstrap_breakglass_enable_impl(
        db_container, bootstrap_user, db_conf, db_name, COMPOSE_FILE
    )


def provision_role_sql(runner: "Runner", target: dict) -> list[str]:
    """Do the actual role/ownership/ACL work for one instance, assuming the
    bootstrap role can already log in (caller's responsibility to
    enable/disable around this — see :func:`provision_instance_role` for the
    single-instance CLI entry point, or :func:`provision_instances_grouped`
    to batch multiple targets of the same service under one enable/disable
    pair and avoid repeated maintenance windows).

    IMPORTANT: never uses ``REASSIGN OWNED`` — run once, connected to one
    database, it reassigns ALL databases cluster-wide still owned by the
    source role, not just the one you're connected to (learned the hard way
    on 2026-08-17). ``ALTER DATABASE ... OWNER TO`` is precise and
    side-effect free, used instead for every ownership change here.
    """
    db_container = target["db_container"]
    bootstrap_user = target["bootstrap_user"]
    bootstrap_password = target["bootstrap_password"]
    db_user = target["db_user"]
    db_password = target["db_password"]
    db_filter = target["db_filter"]

    runner.info(f"\n→ Creando/actualizando rol '{db_user}'...")
    _pg_exec(
        runner, db_container, bootstrap_user, bootstrap_password, "postgres",
        f"CREATE ROLE {db_user} LOGIN CREATEDB NOSUPERUSER NOCREATEROLE "
        f"NOREPLICATION PASSWORD '{db_password}';",
        check=False,
    )
    _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
             f"ALTER ROLE {db_user} WITH PASSWORD '{db_password}';")
    _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
             f"GRANT {bootstrap_user} TO {db_user};")

    list_result = subprocess.run(
        ["docker", "exec", "-e", f"PGPASSWORD={bootstrap_password}", _container_id(db_container),
         "psql", "-U", bootstrap_user, "-d", "postgres", "-tAc",
         f"SELECT datname FROM pg_database WHERE datistemplate=false "
         f"AND datname ~ '{db_filter}';"],
        capture_output=True, text=True, check=True,
    )
    matching = [d.strip() for d in list_result.stdout.splitlines() if d.strip()]
    runner.info(
        f"→ Bases que matchean '{db_filter}': "
        f"{', '.join(matching) if matching else '(ninguna)'}"
    )

    for db in matching:
        runner.info(f"  - {db}")
        _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
                 f'ALTER DATABASE "{db}" OWNER TO {db_user};')
        _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
                 f'REVOKE CONNECT ON DATABASE "{db}" FROM PUBLIC;')
        _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
                 f'GRANT CONNECT ON DATABASE "{db}" TO {db_user};')

    return matching


def provision_instance_role(runner: "Runner", config: dict, instance: str) -> None:
    """CLI entry point: provision a single instance end to end, including its
    own dedicated break-glass window. See :func:`provision_role_sql` for what
    "provision" means, and the module docstring for why this exists
    (Postgres-level fix for cron crossing instances that share a database
    service, instead of patching Odoo's own code)."""
    target = _resolve_provision_target(runner, config, instance)
    db_container = target["db_container"]
    bootstrap_user = target["bootstrap_user"]
    bootstrap_password = target["bootstrap_password"]

    runner.info(f"\n=== 🔐 APROVISIONANDO ROL DEDICADO: {instance.upper()} ===\n")
    runner.info(
        f"Servicio de Postgres: {target['db_name']}  (contenedor: {db_container})"
    )
    runner.info(f"Rol: {target['db_user']}")
    runner.info(f"db_filter usado para resolver bases: {target['db_filter']}")
    runner.warn(
        f"\n⚠️  Si el rol bootstrap de '{target['db_name']}' esta en NOLOGIN (lo "
        f"normal), esto va a requerir una ventana breve de mantenimiento de "
        f"TODO ese servicio (se reinicia {db_container}), no solo de esta "
        f"instancia.\n"
    )

    if not _confirm_or_skip(runner, "¿Continuar?"):
        runner.info("Cancelado.")
        return

    if _bootstrap_needs_breakglass(db_container, bootstrap_user, bootstrap_password):
        _bootstrap_breakglass_enable(
            runner, db_container, bootstrap_user, target["db_conf"], target["db_name"]
        )
    else:
        runner.info(
            f"\n→ Rol bootstrap '{bootstrap_user}' ya puede loguear "
            f"(sesion previa sin cerrar), sigo sin break-glass."
        )

    matching = provision_role_sql(runner, target)

    _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
             f"ALTER ROLE {bootstrap_user} NOLOGIN;")

    runner.info(
        f"\n✅ '{instance}' aprovisionada: rol '{target['db_user']}', dueño de "
        f"{len(matching)} base(s), CONNECT restringido a ese rol.\n"
        f"   Falta: regenerar el compose y recrear el contenedor de esta "
        f"instancia (./odoo build && docker compose up -d --no-deps "
        f"odoo-{instance}) para que use las credenciales nuevas.\n"
    )


# ============================================================
# Batch provisioning + build-time auto-fix
# ============================================================


def _provision_targets_grouped(
    runner: "Runner", config: dict, instance_names: list[str]
) -> dict[str, list[dict]]:
    """Resolve provisioning targets and group them by Postgres service
    (``db_container``) — same pattern used in the original batch migration, so
    one break-glass window is applied per service instead of one per
    instance."""
    targets = [
        _resolve_provision_target(runner, config, name) for name in instance_names
    ]
    groups = defaultdict(list)
    for t in targets:
        groups[t["db_container"]].append(t)
    return groups


def provision_instances_grouped(
    runner: "Runner", config: dict, instance_names: list[str]
) -> None:
    """Provision several instances at once, grouping by Postgres service to
    minimise maintenance windows. Used by ``./odoo build``'s interactive flow
    when the operator confirms fixing the drift found by the audit (see
    :func:`maybe_fix_drift`)."""
    groups = _provision_targets_grouped(runner, config, instance_names)
    for db_container, group in groups.items():
        bootstrap_user = group[0]["bootstrap_user"]
        bootstrap_password = group[0]["bootstrap_password"]
        db_conf = group[0]["db_conf"]
        db_name = group[0]["db_name"]

        runner.info(f"\n--- Servicio {db_container}: {len(group)} instancia(s) ---")
        for t in group:
            runner.info(f"  - {t['instance']} (rol {t['db_user']})")

        if _bootstrap_needs_breakglass(db_container, bootstrap_user, bootstrap_password):
            _bootstrap_breakglass_enable(
                runner, db_container, bootstrap_user, db_conf, db_name
            )
        else:
            runner.info("→ Bootstrap ya logueable, sin break-glass.")

        for t in group:
            runner.info(f"\n--- {t['instance']} ---")
            provision_role_sql(runner, t)

        _pg_exec(runner, db_container, bootstrap_user, bootstrap_password, "postgres",
                 f"ALTER ROLE {bootstrap_user} NOLOGIN;")
        runner.info(
            f"\n✅ Servicio {db_container} listo, bootstrap de nuevo en NOLOGIN."
        )


def _confirm_or_skip(runner: "Runner", prompt: str) -> bool:
    """``runner.confirm`` that answers "no" instead of blowing up when there
    is no interactive input at all.

    Required by ``openspec/specs/postgres-security/spec.md``: a build with no
    keyboard available (CI/automation) must complete without launching any
    auto-correction AND without failing for lack of interactive input.
    ``CliRunner.confirm`` falls back to ``input()`` on a non-TTY stdin, which
    raises ``EOFError`` when stdin is closed — that must not propagate.
    """
    try:
        return runner.confirm(prompt, default=False)
    except EOFError:
        runner.info(
            "\n(sin entrada interactiva -- se omite; correr "
            "'./odoo provision-role <instancia>' a mano)\n"
        )
        return False


def maybe_fix_drift(
    runner: "Runner", config: dict, findings: list[dict], no_confirm: bool
) -> None:
    """If the audit found unambiguously fixable differences (wrong owner,
    ``CONNECT`` not revoked), offer to fix them right now with
    ``provision-role``, grouped by service. Ambiguous findings (filter
    changed, overlapping filters) are never auto-corrected — they need human
    review before touching ownership."""
    fixable_instances = sorted({
        f["instance"] for f in findings if f["fixable"] and f["instance"]
    })
    if not fixable_instances:
        return

    runner.warn(
        f"{len(fixable_instances)} instancia(s) con diferencias que "
        f"'provision-role' puede corregir automaticamente: "
        f"{', '.join(fixable_instances)}"
    )

    if no_confirm:
        runner.info(
            "--no-confirm: se omite la correccion automatica -- correr "
            "'./odoo provision-role <instancia>' a mano si hace falta.\n"
        )
        return

    if not _confirm_or_skip(runner, "¿Correr 'provision-role' para todas ellas ahora?"):
        runner.info("Se omite la correccion automatica.\n")
        return

    provision_instances_grouped(runner, config, fixable_instances)


__all__ = [
    "audit_db_filter_drift",
    "maybe_fix_drift",
    "print_db_filter_audit",
    "provision_instance_role",
    "provision_instances_grouped",
    "provision_role_sql",
]


# ============================================================
# psql: conexión sin filtrar (--ps) y borrado de bases (remove)
# ============================================================


def _list_all_databases(
    runner: "Runner", db_container: str, pg_user: str, pg_password: str
) -> list[str] | None:
    """Lista todas las bases reales (no template) de un servicio de Postgres,
    conectando directo al contenedor de la base con el rol dado. Devuelve
    ``None`` (y ya imprimió el error) si el listado en sí falla."""
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "exec", "-T",
         "-e", f"PGPASSWORD={pg_password}", db_container,
         "psql", "-U", pg_user, "-d", "postgres", "-tAc",
         "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if result.stdout:
            runner.info(result.stdout.rstrip())
        if result.stderr:
            runner.error(result.stderr.rstrip())
        runner.error("❌ No se pudieron listar las bases.")
        return None
    return [d.strip() for d in result.stdout.splitlines() if d.strip()]


def _drop_database(
    runner: "Runner",
    service: str,
    pg_user: str,
    pg_password: str,
    dbname: str,
    host_args: list[str] | None = None,
) -> bool:
    """Ejecuta ``dropdb`` contra ``dbname``. Si falla porque hay sesiones
    activas (el caso normal mientras la instancia de Odoo sigue corriendo —
    mantiene un pool de conexiones abierto), ofrece terminarlas
    (``pg_terminate_backend``) y reintenta una vez, en vez de obligar a un
    ``./odoo stop <instancia>`` manual antes de poder borrar una base cuyo
    borrado ya se confirmó."""
    host_args = host_args or []
    base = [
        "docker", "compose", "-f", COMPOSE_FILE, "exec", "-T",
        "-e", f"PGPASSWORD={pg_password}", service,
    ]

    def run_dropdb() -> subprocess.CompletedProcess:
        return subprocess.run(
            [*base, "dropdb", "-U", pg_user, *host_args, dbname],
            capture_output=True, text=True,
        )

    result = run_dropdb()
    if result.returncode == 0:
        return True

    if "being accessed by other users" in result.stderr:
        runner.error(result.stderr.strip())
        if not runner.confirm(
            "\n¿Terminar esas sesiones activas y reintentar el borrado?"
        ):
            return False

        subprocess.run(
            [*base, "psql", "-U", pg_user, *host_args, "-d", "postgres", "-tAc",
             f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
             f"WHERE datname = '{dbname}' AND pid <> pg_backend_pid();"],
            capture_output=True, text=True,
        )
        result = run_dropdb()
        if result.returncode == 0:
            return True

    if result.stdout:
        runner.info(result.stdout.rstrip())
    if result.stderr:
        runner.error(result.stderr.rstrip())
    return False


def _confirm_drop(runner: "Runner", dbnames: list[str], scope_desc: str) -> bool:
    """Confirm gate para ``DROP DATABASE``, mismo estilo (y mismo nivel de
    fricción) que ``remove_odoo()`` usa para eliminar contenedores/volúmenes —
    consistente en toda la CLI, y obligatorio para cualquier operación que
    borre datos sin vuelta atrás. Con varias bases las lista todas antes de
    pedir una única confirmación."""
    if len(dbnames) == 1:
        runner.warn(
            f"\n⚠️  PELIGRO: esto eliminará (DROP DATABASE) '{dbnames[0]}' de "
            f"{scope_desc}. Esto NO se puede deshacer."
        )
    else:
        listado = "\n".join(f"  - {d}" for d in dbnames)
        runner.warn(
            f"\n⚠️  PELIGRO: esto eliminará (DROP DATABASE) {len(dbnames)} "
            f"base(s) de datos de {scope_desc}:\n{listado}\n"
            f"Esto NO se puede deshacer."
        )
    return runner.confirm("¿Estás seguro de que deseas continuar?")


def _prompt_pg_service(runner: "Runner", config: dict) -> tuple | None:
    """Elegí un servicio de Postgres y devolvé todo lo que hace falta para
    hablarle con el rol bootstrap. ``None`` si el usuario cancela."""
    from generators.config_loader import (
        get_managed_databases,
        resolve_db_bootstrap_creds,
    )

    managed = get_managed_databases(config)
    if not managed:
        runner.error("No hay servicios de base de datos administrados en instances.json.")
        sys.exit(1)

    db_name = runner.select_one(
        "Selecciona el servicio de Postgres", [(name, name) for name in managed]
    )
    if db_name is None:
        runner.info("No se seleccionó ningún servicio.")
        return None

    db_conf = config["databases"][db_name]
    db_container = f"db-{db_name}"
    bootstrap_user, bootstrap_password = resolve_db_bootstrap_creds(db_conf)

    runner.warn(
        f"\n⚠️  Vas a entrar con el rol bootstrap ('{bootstrap_user}'), que ve "
        f"TODAS las bases de '{db_name}' sin filtrar por instancia. Si está en "
        f"NOLOGIN (lo normal), esto requiere una ventana breve de mantenimiento "
        f"de TODO el servicio (se reinicia {db_container}), no solo de una "
        f"instancia puntual."
    )
    if not runner.confirm("¿Continuar?"):
        runner.info("Cancelado.")
        return None

    if _bootstrap_needs_breakglass(db_container, bootstrap_user, bootstrap_password):
        _bootstrap_breakglass_enable(
            runner, db_container, bootstrap_user, db_conf, db_name
        )
    else:
        runner.info(
            f"\n→ Rol bootstrap '{bootstrap_user}' ya puede loguear (sesión "
            f"previa sin cerrar), sigo sin break-glass."
        )

    return db_name, db_container, bootstrap_user, bootstrap_password


def _relock_bootstrap(
    runner: "Runner", db_container: str, bootstrap_user: str, bootstrap_password: str
) -> None:
    runner.info(
        f"\n→ Volviendo a poner el rol bootstrap '{bootstrap_user}' en NOLOGIN..."
    )
    _pg_exec(
        runner, db_container, bootstrap_user, bootstrap_password, "postgres",
        f"ALTER ROLE {bootstrap_user} NOLOGIN;", check=False,
    )


def psql_connect_all(runner: "Runner", config: dict) -> None:
    """Conectar por psql a CUALQUIER base de un servicio de Postgres, sin
    filtrar por instancia/db_filter.

    Hace falta porque, una vez que una instancia se aprovisiona con su rol
    dedicado (``./odoo provision-role``), se le revoca el CONNECT a cualquier
    otro rol sobre sus bases (ver :func:`provision_role_sql`) — ya no existe
    un rol "de menor privilegio" que pueda ver todo el servicio. La única
    llave que abre todas las puertas es el rol bootstrap, y se mantiene en
    NOLOGIN en reposo a propósito. Por eso esto lo habilita solo brevemente
    (break-glass), te deja elegir una base entre TODAS las reales, y siempre
    lo vuelve a poner en NOLOGIN al salir, incluso si algo falla.
    """
    selected = _prompt_pg_service(runner, config)
    if selected is None:
        return
    db_name, db_container, bootstrap_user, bootstrap_password = selected

    try:
        all_dbs = _list_all_databases(
            runner, db_container, bootstrap_user, bootstrap_password
        )
        if not all_dbs:
            if all_dbs is not None:
                runner.info(f"No hay bases en '{db_name}'.")
            return

        dbname = runner.select_one(
            f"Selecciona base de datos en '{db_name}' (TODAS, sin filtrar)",
            [(d, d) for d in all_dbs],
        )
        if dbname is None:
            runner.info("No se seleccionó ninguna base de datos.")
            return

        runner.info(
            f"\n=== 🐘 CONECTANDO PSQL (bootstrap, SIN filtrar) A: "
            f"{db_name.upper()} (DB: {dbname}) ===\n"
        )
        runner.run_interactive(
            ["docker", "compose", "-f", COMPOSE_FILE, "exec", "-it",
             "-e", f"PGPASSWORD={bootstrap_password}", db_container,
             "psql", "-U", bootstrap_user, "-d", dbname],
            cwd=".",
        )
    finally:
        _relock_bootstrap(runner, db_container, bootstrap_user, bootstrap_password)


def psql_remove_database(
    runner: "Runner", config: dict, instance: str | None, dbname: str | None, use_ps: bool
) -> None:
    """Elimina (DROP DATABASE) una o varias bases. Siempre pide confirmación
    explícita (ver :func:`_confirm_drop`) porque es irreversible.

    Sin ``--ps``: usa el rol de la instancia (dueño de sus propias bases vía
    ``provision-role``, o el rol compartido del servicio en instancias sin
    aprovisionar) — mismo camino de credenciales que ``psql_connect()``, sin
    necesitar el rol bootstrap.

    Con ``--ps``: ignora instancias/db_filter y deja elegir CUALQUIER base de
    CUALQUIER servicio, autenticando con el rol bootstrap.
    """
    from generators.config_loader import (
        resolve_db_config,
        resolve_instance_db_creds,
        get_db_host,
        get_db_internal_port,
    )
    from odoo_cli.core.instance import get_databases
    from odoo_cli.core.prompts import prompt_for_database, prompt_for_instance

    if use_ps:
        selected = _prompt_pg_service(runner, config)
        if selected is None:
            return
        db_name, db_container, bootstrap_user, bootstrap_password = selected

        try:
            all_dbs = _list_all_databases(
                runner, db_container, bootstrap_user, bootstrap_password
            )
            if not all_dbs:
                if all_dbs is not None:
                    runner.info(f"No hay bases en '{db_name}'.")
                return

            target_dbs = [dbname] if dbname else runner.select_many(
                f"Selecciona base(s) de datos en '{db_name}' a ELIMINAR "
                f"(TODAS, sin filtrar)",
                [(d, d) for d in all_dbs],
            )
            if not target_dbs:
                runner.info("No se seleccionó ninguna base de datos.")
                return
            invalidas = [d for d in target_dbs if d not in all_dbs]
            if invalidas:
                runner.error(
                    f"Error: {', '.join(invalidas)} no existe(n) en el servicio "
                    f"'{db_name}'."
                )
                sys.exit(1)

            if not _confirm_drop(
                runner, target_dbs, f"servicio de Postgres '{db_name}'"
            ):
                runner.info("Cancelado.")
                return

            hubo_error = False
            for target_db in target_dbs:
                runner.info(f"\n→ Eliminando base de datos '{target_db}' en '{db_name}'...")
                if _drop_database(
                    runner, db_container, bootstrap_user, bootstrap_password, target_db
                ):
                    runner.info(f"✅ Base de datos '{target_db}' eliminada.")
                else:
                    runner.error(f"❌ No se pudo eliminar la base de datos '{target_db}'.")
                    hubo_error = True
            if hubo_error:
                sys.exit(1)
        finally:
            _relock_bootstrap(runner, db_container, bootstrap_user, bootstrap_password)
        return

    if instance is None:
        instance = prompt_for_instance(runner, config, "psql")

    if dbname:
        target_dbs = [dbname]
    else:
        databases = get_databases(config, instance)
        if databases:
            target_dbs = runner.select_many(
                f"Selecciona base(s) de datos para '{instance}' a ELIMINAR",
                [(db, db) for db in databases],
            )
        else:
            single = prompt_for_database(runner, config, instance)
            target_dbs = [single] if single else []
    if not target_dbs:
        runner.info("No se seleccionó ninguna base de datos.")
        return

    inst_conf = config["instances"][instance]
    db_conf = resolve_db_config(inst_conf, config)
    db_host = get_db_host(inst_conf["database"], db_conf)
    db_user, db_password = resolve_instance_db_creds(inst_conf, db_conf)
    db_port = get_db_internal_port(db_conf)
    service = f"odoo-{instance}"

    if not _confirm_drop(runner, target_dbs, f"instancia '{instance}'"):
        runner.info("Cancelado.")
        return

    host_args = ["--host", db_host, "--port", str(db_port)]
    hubo_error = False
    for target_db in target_dbs:
        runner.info(f"\n→ Eliminando base de datos '{target_db}' de '{instance}'...")
        if _drop_database(
            runner, service, db_user, db_password, target_db, host_args=host_args
        ):
            runner.info(f"✅ Base de datos '{target_db}' eliminada.")
        else:
            runner.error(f"❌ No se pudo eliminar la base de datos '{target_db}'.")
            hubo_error = True
    if hubo_error:
        sys.exit(1)
