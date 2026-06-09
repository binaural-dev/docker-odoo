"""
Discovery tools - list instances, databases, and get instance info.
"""

import json
from typing import Dict, List

from .config import Config


def list_instances(config: Config) -> str:
    """List all configured Odoo instances with their version, port, and database."""
    instances = config.get_instances()
    if not instances:
        return "No instances configured."

    result = []
    for name, inst in sorted(instances.items()):
        result.append({
            "name": name,
            "odoo_version": inst.odoo_version,
            "external_port": inst.external_port,
            "database": inst.database,
            "url": f"http://localhost:{inst.external_port}",
        })

    return json.dumps(result, indent=2)


def list_databases(config: Config) -> str:
    """List all configured PostgreSQL databases."""
    databases = config.get_databases()
    if not databases:
        return "No databases configured."

    result = []
    for name, db in sorted(databases.items()):
        result.append({
            "name": name,
            "postgres_version": db.postgres_version,
            "host": db.host,
            "port": db.port,
            "user": db.user,
            "create_container": db.create_container,
        })

    return json.dumps(result, indent=2)


def instance_info(config: Config, instance_name: str) -> str:
    """Get detailed information about a specific Odoo instance."""
    inst = config.get_instance(instance_name)
    if not inst:
        available = ", ".join(sorted(config.get_instances().keys()))
        return f"Instance '{instance_name}' not found. Available: {available}"

    db = config.get_database(inst.database)

    info = {
        "name": inst.name,
        "odoo_version": inst.odoo_version,
        "external_port": inst.external_port,
        "url": f"http://localhost:{inst.external_port}",
        "database": {
            "name": inst.database,
            "host": db.host if db else "unknown",
            "port": db.port if db else "unknown",
            "user": db.user if db else "unknown",
        },
        "odoo_config": inst.odoo_config,
        "addons": inst.addons,
    }

    return json.dumps(info, indent=2)
