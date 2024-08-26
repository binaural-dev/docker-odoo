#!/bin/bash
set -e

echo "Running entrypoint.d..."
$RESOURCES/entrypoint

echo "Running command... $@"
case "$1" in
    --)
        shift
        echo "$@"
        exec $ODOO_SERVER "$@"
        ;;
    -*)
        echo "$@"
        exec $ODOO_SERVER "$@"
        ;;
    *)
        echo "$@"
        exec "$@"
esac
