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
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from odoo_cli.core.actions.lifecycle import COMPOSE_FILE


def _container_id(service: str) -> str:
    """Resolve a compose service name to its real container ID.

    ``docker compose`` names containers ``<project>-<service>-<n>``, not
    the bare service name — raw ``docker exec``/``docker inspect`` calls
    against the service name fail with 'no such object' whenever the
    compose project has a name prefix (the normal case). ``docker compose
    ps -q`` is what actually knows the mapping.
    """
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "ps", "-q", service],
        capture_output=True, text=True,
    )
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError(
            f"No se encontró un contenedor corriendo para el servicio "
            f"'{service}' (¿está levantado con 'docker compose up'?)."
        )
    return container_id

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


def _bootstrap_needs_breakglass(
    db_container: str, bootstrap_user: str, bootstrap_password: str
) -> bool:
    check = subprocess.run(
        ["docker", "exec", "-e", f"PGPASSWORD={bootstrap_password}", _container_id(db_container),
         "psql", "-U", bootstrap_user, "-d", "postgres", "-tAc", "SELECT 1;"],
        capture_output=True,
    )
    return check.returncode != 0


def _bootstrap_breakglass_enable(
    runner: "Runner", db_container: str, bootstrap_user: str, db_conf: dict, db_name: str
) -> None:
    """Stop the db service, flip the bootstrap role to ``LOGIN`` via
    ``postgres --single`` (bypasses normal auth — the only way in once
    ``NOLOGIN``, since creating roles needs ``CREATEROLE``), then start it
    back up."""
    runner.warn(
        f"\n→ Rol bootstrap '{bootstrap_user}' no puede loguear, "
        f"aplicando break-glass en {db_container}..."
    )
    pg_version = db_conf["postgres_version"]
    from generators.compose_generator import _project_slug

    image = f"local_odoo_db_{_project_slug('.')}_{db_name}:{pg_version}"
    volume = subprocess.check_output(
        ["docker", "inspect", _container_id(db_container), "--format",
         '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}']
    ).decode().strip()
    if not volume:
        runner.error(
            f"Error: no se pudo determinar el volumen de datos de {db_container}."
        )
        sys.exit(1)

    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "stop", db_container])
    subprocess.run(
        ["docker", "run", "--rm", "-i", "--user", "postgres",
         "-v", f"{volume}:/var/lib/postgresql/data",
         "--entrypoint", "", image,
         "postgres", "--single", "-D", "/var/lib/postgresql/data/pgdata", "postgres"],
        input=f"ALTER ROLE {bootstrap_user} LOGIN;", text=True,
    )
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", db_container])
    runner.info("→ Esperando a que el servicio vuelva a estar disponible...")
    time.sleep(6)


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
