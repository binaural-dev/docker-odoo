#!/bin/bash
# pgvector is only installed at image-build time (see db.Dockerfile) when the
# database group opts in with "pgvector": true in instances.json -- most
# groups don't need it, so they get a plain postgres image with no extra
# package/attack surface. PGVECTOR_ENABLED (set by compose_generator.py from
# that same flag) tells us here whether this particular container had it
# installed at all.
#
# This script runs later, inside docker-entrypoint-initdb.d, where Postgres
# always drops privileges to the non-root 'postgres' OS user -- so apt-get
# here would fail with "Permission denied" on any brand-new data volume.
# This just confirms the package landed correctly instead of trying to
# (re)install it.
#
# Beyond checking availability, we also CREATE EXTENSION vector inside
# template1. Every instance database in this project is created with a plain
# `CREATE DATABASE <name>;` (see scripts/restore_db.sh and Odoo's own db
# manager), which without an explicit TEMPLATE clause always clones
# template1. So installing the extension there -- once, here -- makes it
# show up already-activated in every instance database created afterwards,
# without needing a manual `CREATE EXTENSION vector;` per database.
set -e

if [ "${PGVECTOR_ENABLED:-false}" != "true" ]; then
  echo "PGVECTOR_ENABLED is not 'true' -- skipping pgvector setup for this database group."
  exit 0
fi

echo "Checking PostgreSQL extensions..."

VERSION=$(psql -V | awk '{print $3}' | cut -d. -f1)
echo "Detected PostgreSQL version: $VERSION"

if [ "$VERSION" -ge 16 ]; then
  if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -tAc \
      "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'" | grep -q 1; then
    echo "pgvector extension package available for PostgreSQL ${VERSION}."

    echo "Activating pgvector in 'template1' so future databases inherit it..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname template1 -c \
        "CREATE EXTENSION IF NOT EXISTS vector;"

    echo "Activating pgvector in '${POSTGRES_DB:-postgres}' (the bootstrap database)..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${POSTGRES_DB:-postgres}" -c \
        "CREATE EXTENSION IF NOT EXISTS vector;"
  else
    echo "WARNING: pgvector package not found -- check the apt-get step in db.Dockerfile." >&2
  fi
fi
