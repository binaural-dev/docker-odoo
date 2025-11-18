#!/bin/bash
set -e

echo "Installing PostgreSQL extensions..."

VERSION=$(psql -V | awk '{print $3}' | cut -d. -f1)

echo "Detected PostgreSQL version: $VERSION"


if [ "$VERSION" -ge 16 ]; then
  echo "Installing pgvector extension for PostgreSQL ${VERSION}..."
  apt-get update
  apt-get install -y postgresql-${VERSION}-pgvector
  rm -rf /var/lib/apt/lists/*

  echo "pgvector extension installed."
fi