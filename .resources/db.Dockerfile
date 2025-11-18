ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}


COPY .resources/db_install_extensions.sh /docker-entrypoint-initdb.d/db_install_extensions.sh
RUN chmod +x /docker-entrypoint-initdb.d/db_install_extensions.sh

RUN /docker-entrypoint-initdb.d/db_install_extensions.sh