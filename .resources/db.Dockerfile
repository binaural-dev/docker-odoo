ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}

USER root
COPY .resources/db_install_extensions.sh /docker-entrypoint-initdb.d/install_extensions.sh
RUN chmod +x /docker-entrypoint-initdb.d/install_extensions.sh
USER postgres