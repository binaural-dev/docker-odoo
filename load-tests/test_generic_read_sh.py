# -*- coding: utf-8 -*-
"""
Test genérico de lectura OPTIMIZADO para Odoo.sh
Incluye timeout mayor para soportar instancias que pueden estar dormidas.

Uso:
    locust -f test_generic_read_sh.py --host=https://TU-DOMINIO.odoo.com
"""

from locust import task, between
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

from OdooLocust.OdooLocustUser import OdooLocustUser
from instances_config import get_instance_config


class GenericReadUser(OdooLocustUser):
    """
    Usuario que realiza operaciones de lectura genéricas en Odoo.sh
    
    CONFIGURACIÓN OBLIGATORIA:
    1. Edita 'instance_name' con el nombre de tu instancia en instances_config.py
    2. O sobrescribe directamente los valores host, port, database, etc.
    """
    abstract = False
    
    # ============== CONFIGURA ESTO ==============
    instance_name = "petare"  # <-- Cambia esto
    # ============================================
    
    # Timeout mayor para Odoo.sh (instancias pueden estar dormidas)
    timeout = 60
    
    # Tiempo entre operaciones (simula comportamiento real)
    wait_time = between(2, 5)  # Más tiempo para no saturar SH
    
    def __init__(self, environment):
        super().__init__(environment)
        
        # Cargar configuración desde instances_config.py
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
                    f"Instancia '{self.instance_name}' no encontrada. "
                    f"Verifica instances_config.py"
                )

    def on_start(self):
        """Inicializa la conexión al inicio de cada usuario."""
        super().on_start()
        # Guardar modelos para reutilizar
        try:
            self.partner_model = self.client.get_model('res.partner')
            self.product_model = self.client.get_model('product.product')
            print(f"✅ Usuario conectado a {self.host}")
        except Exception as e:
            print(f"❌ Error al inicializar modelos: {e}")
            raise

    @task(10)
    def read_partners(self):
        """Lee partners (clientes/proveedores)."""
        try:
            partner_ids = self.partner_model.search([], limit=20)  # Menos registros para SH
            if partner_ids:
                self.partner_model.read(partner_ids, ['name', 'email'])
        except Exception as e:
            pass

    @task(5)
    def read_products(self):
        """Lee productos."""
        try:
            product_ids = self.product_model.search([('sale_ok', '=', True)], limit=10)
            if product_ids:
                self.product_model.read(product_ids, ['name', 'list_price'])
        except Exception as e:
            pass
