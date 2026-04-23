#!/bin/bash
set -e

echo "Running entrypoint.d..."
$RESOURCES/entrypoint

echo "Running command... $@"
export PYTHONPATH="/opt/venv/lib/python3.12/site-packages:$PYTHONPATH"
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
