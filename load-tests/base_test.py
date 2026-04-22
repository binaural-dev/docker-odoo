# -*- coding: utf-8 -*-
"""
Test base genérico para pruebas de estrés en Odoo.
Este archivo contiene la clase base que todos los tests deben extender.
"""

import sys
import os

# Agregar el path de OdooLocust al sys.path
ODOOLOCUST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "OdooLocust",
    "src"
)
if ODOOLOCUST_PATH not in sys.path:
    sys.path.insert(0, ODOOLOCUST_PATH)

from locust import task, between
from OdooLocust.OdooLocustUser import OdooLocustUser
from instances_config import get_instance_config


class BaseOdooUser(OdooLocustUser):
    """
    Clase base para usuarios de pruebas de estrés en Odoo.

    Para usar esta clase, extiéndela y define:
    - instance_name: Nombre de la instancia definida en instances_config.py
    - tasks: Diccionario de tareas con sus pesos

    Ejemplo:
        class MyUser(BaseOdooUser):
            instance_name = "cadipa1"
            wait_time = between(1, 5)

            @task(10)
            def my_task(self):
                # Tu código aquí
                pass
    """
    abstract = True
    instance_name = None  # Sobreescribir en subclase

    def __init__(self, environment):
        super().__init__(environment)

        if self.instance_name:
            config = get_instance_config(self.instance_name)
            if config:
                self.host = config["host"]
                self.port = config["port"]
                self.database = config["database"]
                self.login = config["login"]
                self.password = config["password"]
                self.protocol = config["protocol"]
            else:
                raise ValueError(
                    f"Instancia '{self.instance_name}' no encontrada en instances_config.py"
                )
