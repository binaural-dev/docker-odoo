"""
Shared helpers for operating on a Postgres service's bootstrap (initdb) role.

db_create_app_role.sh locks that role to NOLOGIN right after the cluster is
created, so it's never used day to day (see that script). Both
`./odoo provision-role` and `scripts/odoo_restore` occasionally need a
privileged one-off operation on the cluster (creating/altering roles,
granting SUPERUSER for a dump that needs CREATE EXTENSION) and have to
temporarily break that lock to do it. This module is the one place that
break-glass logic lives, so both callers stay in sync.
"""

import os
import subprocess
import sys
import time


def pg_exec(db_container, pg_user, pg_password, dbname, sql, check=True):
    """Run one SQL statement via docker exec, as argv (not a shell string) so
    nested double-quoted Postgres identifiers can't collide with shell quoting."""
    result = subprocess.run(
        [
            "docker", "exec", "-e", f"PGPASSWORD={pg_password}", db_container,
            "psql", "-U", pg_user, "-d", dbname, "-v", "ON_ERROR_STOP=1", "-c", sql,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        if check:
            sys.exit(1)
    return result


def bootstrap_needs_breakglass(db_container, bootstrap_user, bootstrap_password):
    """True if the bootstrap role can't currently log in (the normal,
    hardened state after provisioning)."""
    check = subprocess.run(
        ["docker", "exec", "-e", f"PGPASSWORD={bootstrap_password}", db_container,
         "psql", "-U", bootstrap_user, "-d", "postgres", "-tAc", "SELECT 1;"],
        capture_output=True,
    )
    return check.returncode != 0


def bootstrap_breakglass_enable(db_container, bootstrap_user, db_conf, db_name, compose_file):
    """Stop the db service, flip the bootstrap role to LOGIN via
    `postgres --single` (bypasses normal auth -- the only way in once
    NOLOGIN, since altering a role needs CREATEROLE), then start it back up.

    Affects the whole Postgres service (every instance sharing it), not just
    the caller's instance -- callers should batch privileged work under one
    enable/disable pair rather than breaking glass repeatedly.
    """
    print(f"\n→ Rol bootstrap '{bootstrap_user}' no puede loguear, aplicando break-glass en {db_container}...")
    pg_version = db_conf["postgres_version"]
    image = f"local_odoo_db_{db_name}:{pg_version}"
    volume = subprocess.check_output(
        ["docker", "inspect", db_container, "--format",
         '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}']
    ).decode().strip()
    if not volume:
        print(f"Error: no se pudo determinar el volumen de datos de {db_container}.")
        sys.exit(1)

    os.system(f"docker compose -f {compose_file} stop {db_container}")
    subprocess.run(
        ["docker", "run", "--rm", "-i", "--user", "postgres",
         "-v", f"{volume}:/var/lib/postgresql/data",
         "--entrypoint", "", image,
         "postgres", "--single", "-D", "/var/lib/postgresql/data/pgdata", "postgres"],
        input=f"ALTER ROLE {bootstrap_user} LOGIN;", text=True,
    )
    os.system(f"docker compose -f {compose_file} up -d {db_container}")
    print("→ Esperando a que el servicio vuelva a estar disponible...")
    time.sleep(6)
