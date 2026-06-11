"""
Helpers compartidos para ./odoo pw y scripts/odoo-pw.

Validaciones que viven en ambos entry points:
- _check_db_exists: valida que la DB exista en el contenedor psql
  objetivo, antes de correr el UPDATE. Si no existe, devuelve
  (False, lista_de_dbs_disponibles) para que el caller aborte
  con un mensaje claro.
"""

import subprocess


def _check_db_exists(container, db_host, db_user, db_port, db_password, dbname):
    """Comprueba que ``dbname`` exista en el contenedor PostgreSQL.

    Devuelve una tupla ``(existe, disponibles)``:
      - ``existe`` (bool): True si la DB esta, False si no.
      - ``disponibles`` (list[str]): nombres de bases NO-template
        en el contenedor (puede ser lista vacia si la consulta
        fallo). Solo relevante cuando ``existe`` es False.

    Implementacion: corre ``psql -d postgres -c 'SELECT 1 FROM
    pg_database WHERE datname=...'`` y ``psql -d postgres -c
    'SELECT datname FROM pg_database WHERE datistemplate=false'``
    y devuelve segun el output. Si psql retorna rc != 0, ``existe``
    es False y la lista de disponibles es vacia (no podemos
    saber mas sin acceso a la DB).
    """
    env = {"PGPASSWORD": db_password, "PATH": "/usr/bin:/bin:/usr/local/bin"}
    psql_base = [
        "docker", "exec", container,
        "psql",
        "--host", db_host,
        "--port", str(db_port),
        "-U", db_user,
        "-d", "postgres",
    ]

    # 1) SELECT 1 para la DB objetivo
    check = subprocess.run(
        psql_base + [
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{dbname}'",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        return False, []
    existe = "1" in (check.stdout or "").strip().splitlines()

    if existe:
        return True, []

    # 2) Listar DBs disponibles para mensaje de error
    listing = subprocess.run(
        psql_base + [
            "-tAc",
            "SELECT datname FROM pg_database WHERE datistemplate = false",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    disponibles = [
        line.strip()
        for line in (listing.stdout or "").splitlines()
        if line.strip()
    ]
    return False, disponibles
