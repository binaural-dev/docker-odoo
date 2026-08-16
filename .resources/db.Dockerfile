ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}
ARG POSTGRES_IMG_VERSION

USER root
RUN apt-get update && apt-get install -y postgresql-${POSTGRES_IMG_VERSION}-pgvector && rm -rf /var/lib/apt/lists/*
COPY .resources/db_install_extensions.sh /docker-entrypoint-initdb.d/install_extensions.sh
COPY .resources/db_create_app_role.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh
RUN chmod +x /docker-entrypoint-initdb.d/install_extensions.sh /docker-entrypoint-initdb.d/zz_create_app_role.sh