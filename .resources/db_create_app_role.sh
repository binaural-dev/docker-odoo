#!/bin/bash
# Runs only on a brand-new data volume (docker-entrypoint-initdb.d scripts never
# run again once PGDATA already exists). $POSTGRES_USER is Postgres's initdb
# bootstrap role -- it is always created as a superuser and Postgres refuses to
# ever strip that attribute from it (hard restriction, not a config choice).
# So instead of using it for anything ongoing, we create a second, real
# non-superuser role here that Odoo actually connects with, give it ownership
# of the default database plus inherited access to whatever the bootstrap role
# owns (so DDL during module installs/updates keeps working), and then lock
# the bootstrap role out of LOGIN entirely so nothing can authenticate as a
# superuser over the wire, ever.
set -e

if [ -z "$APP_DB_USER" ]; then
  echo "APP_DB_USER not set, skipping app role creation."
  exit 0
fi

echo "Creating non-superuser app role '$APP_DB_USER'..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    CREATE ROLE "$APP_DB_USER" LOGIN CREATEDB NOSUPERUSER NOCREATEROLE NOREPLICATION PASSWORD '$APP_DB_PASSWORD';
    GRANT "$POSTGRES_USER" TO "$APP_DB_USER";
    ALTER DATABASE postgres OWNER TO "$APP_DB_USER";
    ALTER ROLE "$POSTGRES_USER" NOLOGIN;
EOSQL

echo "App role '$APP_DB_USER' ready (non-superuser, CREATEDB, inherits bootstrap ownership)."
echo "Bootstrap role '$POSTGRES_USER' locked to NOLOGIN -- never used directly by Odoo."
