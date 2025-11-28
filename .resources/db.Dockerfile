ARG POSTGRES_IMG_VERSION=16
FROM postgres:${POSTGRES_IMG_VERSION}

USER root
RUN apt-get update && apt-get install -y postgresql-16-pgvector
USER postgres

RUN ls -la /var/lib/postgresql/data/