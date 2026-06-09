"""
Configuration loader for instances.json.
Provides structured access to Odoo instances, databases, and connection info.
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DatabaseConfig:
    name: str
    postgres_version: int
    port: int
    user: str
    password: str
    host: str = "localhost"
    create_container: bool = True
    config: Optional[str] = None


@dataclass
class InstanceConfig:
    name: str
    odoo_version: str
    external_port: int
    database: str
    odoo_config: str
    addons: List[str]
    enabled: bool = True


class Config:
    def __init__(self, instances_json_path: str):
        self.instances_json_path = instances_json_path
        self._data = None
        self._databases: Dict[str, DatabaseConfig] = {}
        self._instances: Dict[str, InstanceConfig] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.instances_json_path):
            raise FileNotFoundError(f"instances.json not found at {self.instances_json_path}")

        with open(self.instances_json_path, "r") as f:
            self._data = json.load(f)

        self._parse_databases()
        self._parse_instances()

    def _parse_databases(self):
        for db_name, db_conf in self._data.get("databases", {}).items():
            self._databases[db_name] = DatabaseConfig(
                name=db_name,
                postgres_version=db_conf["postgres_version"],
                port=db_conf["port"],
                user=db_conf["user"],
                password=db_conf["password"],
                host=db_conf.get("host", "localhost"),
                create_container=db_conf.get("create_container", True),
                config=db_conf.get("config"),
            )

    def _parse_instances(self):
        for inst_name, inst_conf in self._data.get("instances", {}).items():
            if not inst_conf.get("enabled", True):
                continue

            odoo_config_name = inst_conf["odoo_config"]
            odoo_config = self._data.get("odoo_configs", {}).get(odoo_config_name, {})

            overwrite = inst_conf.get("overwrite_odoo_config", {})
            merged_config = {**odoo_config, **overwrite}

            self._instances[inst_name] = InstanceConfig(
                name=inst_name,
                odoo_version=inst_conf["odoo_version"],
                external_port=inst_conf["external_port"],
                database=inst_conf["database"],
                odoo_config=odoo_config_name,
                addons=merged_config.get("addons", []),
                enabled=inst_conf.get("enabled", True),
            )

    def get_databases(self) -> Dict[str, DatabaseConfig]:
        return self._databases

    def get_database(self, name: str) -> Optional[DatabaseConfig]:
        return self._databases.get(name)

    def get_instances(self) -> Dict[str, InstanceConfig]:
        return self._instances

    def get_instance(self, name: str) -> Optional[InstanceConfig]:
        return self._instances.get(name)

    def get_instance_by_db(self, db_name: str) -> List[InstanceConfig]:
        return [inst for inst in self._instances.values() if inst.database == db_name]

    def get_odoo_url(self, instance_name: str) -> str:
        inst = self.get_instance(instance_name)
        if not inst:
            raise ValueError(f"Instance '{instance_name}' not found")
        return f"http://localhost:{inst.external_port}"

    def get_db_connection_params(self, db_name: str) -> Dict:
        db = self.get_database(db_name)
        if not db:
            raise ValueError(f"Database '{db_name}' not found")
        return {
            "host": db.host,
            "port": db.port,
            "user": db.user,
            "password": db.password,
        }
