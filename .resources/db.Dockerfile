ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}
ARG POSTGRES_IMG_VERSION

USER root
RUN apt-get update && apt-get install -y postgresql-${POSTGRES_IMG_VERSION}-pgvector && rm -rf /var/lib/apt/lists/*
# Mark pgvector as a trusted extension so the (non-superuser) instance role
# can `CREATE EXTENSION vector` on databases it owns -- Odoo's `ai` module
# runs it in its pre_init hook. The control file lives in the image, not in
# PGDATA, so this also applies to existing data volumes after a rebuild.
RUN CONTROL=/usr/share/postgresql/${POSTGRES_IMG_VERSION}/extension/vector.control \
    && test -f "$CONTROL" \
    && { grep -q '^trusted' "$CONTROL" || echo 'trusted = true' >> "$CONTROL"; }
COPY .resources/db_install_extensions.sh /docker-entrypoint-initdb.d/install_extensions.sh
COPY .resources/db_create_app_role.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh
RUN chmod +x /docker-entrypoint-initdb.d/install_extensions.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh