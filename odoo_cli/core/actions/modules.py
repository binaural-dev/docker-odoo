"""Module-level update / init / sync / pw actions.

These were the last big function bodies left in ``./odoo`` after
commits 1-6. They share a common shape:

  * A "single shot" function that does the actual work for one
    instance/database combo (``bash_update_modules``,
    ``reset_password``).
  * An "orchestration" function that handles the multi-database
    fan-out / prompt resolution / failure summary
    (``update``).

The orchestration lives in :func:`update` so that the dispatch
(``./odoo update`` → either one DB or all DBs) stays next to the
single-shot function that does the heavy lifting. The CLI's
``main()`` will call :func:`update` after prompting for
``instance``/``dbname``/``modules``; the prompt logic is in
:mod:`odoo_cli.core.prompts`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner


# ============================================================
# Module update (single shot + orchestration)
# ============================================================


def bash_update_modules(
    runner: "Runner",
    config: dict,
    instance: str,
    dbname: str,
    modules: str = "all",
) -> int:
    """Update Odoo modules in an instance (single database).

    Runs ``odoo --stop-after-init -u <modules> -d <dbname>`` inside
    the Odoo container and returns the process returncode. The
    caller is responsible for interpreting the returncode (the
    ``update`` orchestration collects failures across databases).
    """
    runner.info(
        f"\n=== 🆙 ACTUALIZANDO MÓDULOS EN: {instance.upper()} "
        f"(DB: {dbname}) ===\n"
    )
    container = f"odoo-{instance}"
    cmd = [
        "docker", "exec", container, "odoo",
        "--stop-after-init", "--http-port", "9999", "--workers=0",
        "-u", modules, "-d", dbname,
    ]
    runner.info(" ".join(cmd))
    return subprocess.run(cmd).returncode


def update(
    runner: "Runner",
    config: dict,
    instance: str,
    dbname: str,
    modules: str = "all",
) -> None:
    """Update Odoo modules, fanning out to every database when ``dbname=='all'``.

    With ``dbname == "all"`` (case-insensitive), iterates over the
    databases of ``instance`` and runs :func:`bash_update_modules`
    for each. A non-zero returncode on any database is collected;
    the final report is printed via the runner and the process
    exits 1 if any database failed.

    With a specific ``dbname``, delegates straight to
    :func:`bash_update_modules`.
    """
    if dbname.strip().lower() == "all":
        from odoo_cli.core.instance import get_databases

        databases = get_databases(config, instance)
        if not databases:
            runner.error(
                "No se encontraron bases de datos para actualizar."
            )
            sys.exit(1)

        failures: list[tuple[str, int]] = []
        for db_name in databases:
            result = bash_update_modules(runner, config, instance, db_name, modules)
            if result != 0:
                failures.append((db_name, result))

        if failures:
            runner.error(
                "\n❌ Algunas bases fallaron durante la actualización:"
            )
            for db_name, code in failures:
                runner.error(f"  - {db_name} (exit code: {code})")
            sys.exit(1)
    else:
        bash_update_modules(runner, config, instance, dbname, modules)


# ============================================================
# Password reset
# ============================================================


def reset_password(
    runner: "Runner",
    config: dict,
    instance: str,
    dbname: str,
    login: str,
    password: str,
) -> None:
    """Reset a user's password in the given database.

    The function does three things in order:

      1. Verify the target database exists in the container (without
         this check, ``psql`` fails cryptically and the user has no
         way to know whether the password was reset).
      2. Verify the login exists in ``res_users`` (case-sensitive).
         If the exact login is missing, fall back to a
         case-insensitive search and suggest the right casing.
      3. Run the ``UPDATE res_users SET password = ...`` SQL and
         verify the row was actually updated (so we can detect a
         race with another process that deletes the user between
         our SELECT and our UPDATE).
    """
    from generators.config_loader import (
    resolve_db_config, get_db_host, get_db_internal_port,
)
    from generators.pw_helpers import _check_db_exists

    runner.info(
        f"\n=== 🔑 RESTABLECIENDO CONTRASEÑA EN: {instance.upper()} "
        f"(Usuario: {login}) ===\n"
    )
    inst_conf = config["instances"][instance]
    db_conf = resolve_db_config(inst_conf, config)
    db_host = get_db_host(inst_conf["database"], db_conf)
    db_user = db_conf["user"]
    db_password = db_conf["password"]
    db_port = get_db_internal_port(db_conf)
    container = f"odoo-{instance}"

    # Validar que la DB exista en el contenedor antes de tocar res_users.
    # Sin esto, psql falla con 'database does not exist' y el usuario
    # no se da cuenta si el returncode no se chequea (o el script termina
    # con error confuso).
    existe, disponibles = _check_db_exists(
        container, db_host, db_user, db_port, db_password, dbname,
    )
    if not existe:
        bases_str = ", ".join(disponibles) if disponibles else "(no se pudo listar)"
        runner.error(
            f"\n✗ La base de datos '{dbname}' no existe en la instancia '{instance}'."
            f"\nBases disponibles en '{instance}': {bases_str}\n"
        )
        sys.exit(1)

    # Validar el login antes de tocar nada: SELECT case-insensitive para
    # detectar typos de mayúsculas (login en Odoo es case-sensitive). Si
    # hay match exacto, ok. Si solo hay case-insensitive, sugerimos el
    # case correcto. Si no hay match, listamos los logins disponibles.
    runner.info(f"\n→ Verificando que el usuario '{login}' exista...")
    safe_login_lit = "'{}'".format(login.replace("'", "''"))
    check_sql = (
        f"SELECT id, login, active FROM res_users "
        f"WHERE login = {safe_login_lit};"
    )
    check_proc = subprocess.run(
        ["docker", "exec", container, "psql", "--host", db_host, "--port", str(db_port),
         "-U", db_user, "-d", dbname, "-tAF", "|", "-c", check_sql],
        env={**os.environ, "PGPASSWORD": db_password},
        capture_output=True,
        text=True,
    )
    if check_proc.returncode != 0:
        runner.error(f"\n✗ Error verificando usuario (código {check_proc.returncode}).\n")
        sys.exit(check_proc.returncode)
    if not check_proc.stdout.strip():
        # Login no existe exacto. Buscar case-insensitive para sugerir el
        # case correcto. No listamos TODOS los logins porque eso expone
        # usuarios reales del cliente (emails, etc.) que el script no
        # deberia mencionar.
        suggest_sql = (
            f"SELECT login FROM res_users "
            f"WHERE LOWER(login) = LOWER({safe_login_lit}) LIMIT 1;"
        )
        suggest_proc = subprocess.run(
            ["docker", "exec", container, "psql", "--host", db_host, "--port", str(db_port),
             "-U", db_user, "-d", dbname, "-tAF", "", "-c", suggest_sql],
            env={**os.environ, "PGPASSWORD": db_password},
            capture_output=True,
            text=True,
        )
        exact_ci = (suggest_proc.stdout or "").strip()
        runner.error(
            f"\n✗ El usuario '{login}' no existe en esta base de datos."
        )
        if exact_ci and exact_ci != login:
            runner.warn(
                f"  → ¿Quisiste decir '{exact_ci}'? (el login es case-sensitive)"
            )
        else:
            runner.info(
                f"  Verificá los logins con: docker exec {container} psql -U {db_user} -d {dbname} "
                f"-c \"SELECT login FROM res_users;\""
            )
        runner.error(
            f"\n  Volvé a correr el comando con el login correcto. "
            f"Ej: ./odoo pw {instance} -d {dbname} -l <login> -p <password>\n"
        )
        sys.exit(1)

    safe_pw = "'{}'".format(password.replace("'", "''"))
    runner.info(
        f"\n→ Restableciendo contraseña para el usuario '{login}' "
        f"en la base de datos '{dbname}'..."
    )
    sql = f"update res_users set password = {safe_pw} where login = {safe_login_lit};"
    proc = subprocess.run(
        ["docker", "exec", container, "psql", "--host", db_host, "--port", str(db_port),
         "-U", db_user, "-d", dbname, "-c", sql],
        env={**os.environ, "PGPASSWORD": db_password},
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        runner.error(
            f"\n✗ Error ejecutando psql (código {proc.returncode}). "
            f"Contraseña NO actualizada.\n"
        )
        sys.exit(proc.returncode)
    if "UPDATE 0" in (proc.stdout or ""):
        # Caso raro: el login existia al validar pero desapareció entre el
        # SELECT y el UPDATE (probable carrera con otro proceso). Reportar
        # para no mentir.
        runner.error(
            f"\n✗ El UPDATE no afectó filas (carrera con otro proceso?)."
            f"\n  Contraseña NO actualizada.\n"
        )
        sys.exit(1)
    runner.info("✅ Contraseña actualizada.\n")


__all__ = [
    "bash_update_modules",
    "reset_password",
    "update",
]
