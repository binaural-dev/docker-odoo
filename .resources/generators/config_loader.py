"""
Loads and validates instances.json configuration.
Resolves odoo_config references and applies overwrite_odoo_config merges.
"""

import json
import os
import sys


def load_config(base_path):
    """Load instances.json from the project root."""
    config_path = os.path.join(base_path, "instances.json")
    if not os.path.exists(config_path):
        print(f"Error: instances.json no encontrado en {base_path}")
        print("Copia instances.example.json a instances.json y configúralo.")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)

    _validate_config(config)
    return config


def _validate_config(config):
    """Validate the configuration structure."""
    required_sections = ["odoo_configs", "databases", "instances"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Sección '{section}' requerida en instances.json")

    if not config["instances"]:
        raise ValueError("Debe haber al menos una instancia definida")

    # Validate each database
    for db_name, db_conf in config["databases"].items():
        _validate_database(db_name, db_conf)

    # Validate each instance
    for inst_name, inst_conf in config["instances"].items():
        _validate_instance(inst_name, inst_conf, config)


def _validate_database(db_name, db_conf):
    """Validate a database configuration."""
    required = ["postgres_version", "port", "user", "password"]
    for field in required:
        if field not in db_conf:
            raise ValueError(
                f"Database '{db_name}': campo '{field}' requerido"
            )

    create_container = db_conf.get("create_container", True)
    if not create_container and "host" not in db_conf:
        raise ValueError(
            f"Database '{db_name}': 'host' requerido cuando create_container=false"
        )


def _validate_instance(inst_name, inst_conf, config):
    """Validate an instance configuration."""
    required = ["odoo_version", "external_port", "database", "odoo_config"]
    for field in required:
        if field not in inst_conf:
            raise ValueError(
                f"Instancia '{inst_name}': campo '{field}' requerido"
            )

    # Validate references
    if inst_conf["database"] not in config["databases"]:
        raise ValueError(
            f"Instancia '{inst_name}': database '{inst_conf['database']}' "
            f"no existe en la sección databases"
        )

    if inst_conf["odoo_config"] not in config["odoo_configs"]:
        raise ValueError(
            f"Instancia '{inst_name}': odoo_config '{inst_conf['odoo_config']}' "
            f"no existe en la sección odoo_configs"
        )

    # Validate unique external_port
    ports = [
        v["external_port"]
        for k, v in config["instances"].items()
    ]
    if len(ports) != len(set(ports)):
        raise ValueError("Los external_port de las instancias deben ser únicos")


def resolve_instance_config(inst_conf, config):
    """
    Resolve the effective odoo config for an instance.
    Takes the base odoo_config and applies overwrite_odoo_config on top.
    """
    base_config_name = inst_conf["odoo_config"]
    base_config = dict(config["odoo_configs"][base_config_name])

    overwrite = inst_conf.get("overwrite_odoo_config", {})
    base_config.update(overwrite)

    return base_config


def resolve_db_config(inst_conf, config):
    """Resolve the database configuration for an instance."""
    db_name = inst_conf["database"]
    return config["databases"][db_name]


def get_db_host(db_name, db_conf):
    """
    Get the DB host for a given database config.
    For managed DBs, returns the container name. For external DBs, returns the host.
    """
    create_container = db_conf.get("create_container", True)
    if create_container:
        return f"db-{db_name}"
    return db_conf["host"]


def get_unique_odoo_versions(config):
    """Get the set of unique Odoo versions across all instances."""
    return set(
        inst["odoo_version"]
        for inst in config["instances"].values()
    )


def get_managed_databases(config):
    """Get databases that need a container (create_container=true or default)."""
    return {
        name: conf
        for name, conf in config["databases"].items()
        if conf.get("create_container", True)
    }


def get_odoo_minor(odoo_version):
    """Extract the minor version number from odoo_version string."""
    if odoo_version == "master":
        return "master"
    return odoo_version.split(".")[0]
