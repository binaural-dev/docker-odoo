"""Ficticios compartidos por los tests de debug remoto.

Instancias dbg-a/dbg-b, DB dbgdb, puertos 28069/28070: nada que ver con
instancias reales. Los tests usan directorios temporales.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_PATH = os.path.join(REPO_ROOT, ".resources")
if RESOURCES_PATH not in sys.path:
    sys.path.insert(0, RESOURCES_PATH)


def debug_config(a_debug=True, b_debug=True, version_a="19.0", version_b="17.0"):
    def inst(version, port, debug):
        d = {
            "odoo_version": version,
            "external_port": port,
            "database": "dbgdb",
            "odoo_config": "base",
            "db_user": f"role_{port}",
            "db_password": "x",
            "overwrite_odoo_config": {"db_filter": f"^dbg{port}"},
        }
        if debug:
            d["debug"] = True
        return d

    return {
        "odoo_configs": {"base": {"admin_password": "admin", "workers": 4}},
        "databases": {
            "dbgdb": {"postgres_version": 16, "port": 26000, "user": "odoo", "password": "odoo"},
        },
        "instances": {
            "dbg-a": inst(version_a, 28069, a_debug),
            "dbg-b": inst(version_b, 28070, b_debug),
        },
    }
