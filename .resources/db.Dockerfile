ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}
ARG POSTGRES_IMG_VERSION
# Opt-in: only the database groups that actually need pgvector (set via
# "pgvector": true on the group in instances.json) pay for installing it.
# Everyone else gets a plain postgres image, no extra package/attack surface.
ARG INSTALL_PGVECTOR=false

USER root
RUN if [ "$INSTALL_PGVECTOR" = "true" ]; then \
        apt-get update && apt-get install -y postgresql-${POSTGRES_IMG_VERSION}-pgvector && rm -rf /var/lib/apt/lists/*; \
    fi
COPY .resources/db_install_extensions.sh /docker-entrypoint-initdb.d/install_extensions.sh
COPY .resources/db_create_app_role.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh
RUN chmod +x /docker-entrypoint-initdb.d/install_extensions.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh