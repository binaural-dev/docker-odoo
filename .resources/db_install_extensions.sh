#!/bin/bash
# pgvector is already installed at image-build time (see db.Dockerfile, which
# runs apt-get as root during the build). This script only runs later, inside
# docker-entrypoint-initdb.d, where Postgres always drops privileges to the
# non-root 'postgres' OS user -- so apt-get here would fail with
# "Permission denied" on any brand-new data volume. This just confirms the
# package landed correctly instead of trying to (re)install it.
set -e

echo "Checking PostgreSQL extensions..."

VERSION=$(psql -V | awk '{print $3}' | cut -d. -f1)
echo "Detected PostgreSQL version: $VERSION"

if [ "$VERSION" -ge 16 ]; then
  if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -tAc \
      "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'" | grep -q 1; then
    echo "pgvector extension package available for PostgreSQL ${VERSION}."
  else
    echo "WARNING: pgvector package not found -- check the apt-get step in db.Dockerfile." >&2
  fi
fi
