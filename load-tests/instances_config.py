# -*- coding: utf-8 -*-
"""
Configuración de instancias Odoo para pruebas de estrés.

IMPORTANTE: El 'database' debe coincidir EXACTAMENTE con el nombre de la
base de datos en PostgreSQL. Puedes ver las bases disponibles con:
    docker exec db-pg16 psql -U odoo -c "\\l"

Edita este archivo para agregar/modificar instancias.
"""

INSTANCES = {
    "binaural_tesote_test": {
        "host": "localhost",
        "port": 8092,
        "database": "binaural_tesote_test",  # Nombre real de la BD en PostgreSQL
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "19.0",
        "description": "Instancia de prueba binaural (Odoo 19)"
    },
    "cadipa1": {
        "host": "localhost",
        "port": 8093,
        "database": "odoo_cadipa1_production",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "17.0",
        "description": "Instancia CADIPA (Odoo 17)"
    },
    "gno": {
        "host": "localhost",
        "port": 8094,
        "database": "odoo_gno_staging",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "17.0",
        "description": "Instancia GNO (Odoo 17)"
    },
    "donaciones": {
        "host": "localhost",
        "port": 8095,
        "database": "odoo_donaciones_prod",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "19.0",
        "description": "Instancia Donaciones (Odoo 19)"
    },
    "17-donaciones": {
        "host": "localhost",
        "port": 8096,
        "database": "odoo_17_donaciones",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "17.0",
        "description": "Instancia Donaciones v17 (Odoo 17)"
    },
    "mercedes": {
        "host": "localhost",
        "port": 8097,
        "database": "19_mercedes",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "19.0",
        "description": "Instancia Mercedes (Odoo 19)"
    },
    "petare": {
        "host": "localhost",
        "port": 8098,
        "database": "odoo_petare_prod",  # Actualizado con nombre real
        "login": "admin",
        "password": "admin",
        "protocol": "jsonrpc",
        "odoo_version": "17.0",
        "description": "Instancia Petare (Odoo 17)"
    },
}


def get_instance_config(instance_name):
    """
    Obtiene la configuración de una instancia.

    Args:
        instance_name: Nombre de la instancia

    Returns:
        dict: Configuración de la instancia o None si no existe
    """
    return INSTANCES.get(instance_name)


def list_instances():
    """
    Lista todas las instancias disponibles.

    Returns:
        dict: Diccionario con nombre y descripción de cada instancia
    """
    return {name: config["description"] for name, config in INSTANCES.items()}
