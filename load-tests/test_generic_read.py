# -*- coding: utf-8 -*-
"""
Test genérico de lectura para cualquier modelo de Odoo.
Prueba operaciones básicas de lectura: search, read, search_count.

Uso:
    locust -f test_generic_read.py --host=http://localhost:PORT
"""

from locust import task, between
from base_test import BaseOdooUser


class GenericReadUser(BaseOdooUser):
    """
    Usuario que realiza operaciones de lectura genéricas.

    Configuración:
    - Modifica 'instance_name' para apuntar a tu instancia
    - Ajusta 'wait_time' según el comportamiento deseado
    """
    abstract = False
    instance_name = "mercedes"
    wait_time = between(0.5, 2)

    def on_start(self):
        """Inicializa la conexión al inicio de cada usuario."""
        super().on_start()
        # Guardar modelos para reutilizar
        self.partner_model = self.client.get_model('res.partner')
        self.product_model = self.client.get_model('product.product')
        self.sale_order_model = self.client.get_model('sale.order')

    @task(10)
    def read_partners(self):
        """
        Lee partners (clientes/proveedores).
        Peso: 10 (muy frecuente)
        """
        try:
            # Buscar hasta 80 partners
            partner_ids = self.partner_model.search([], limit=80)
            if partner_ids:
                # Leer solo campos básicos para ser más rápido
                self.partner_model.read(partner_ids, ['name', 'email', 'phone'])
        except Exception as e:
            # Los errores se registran automáticamente por Locust
            pass

    @task(8)
    def read_products(self):
        """
        Lee productos.
        Peso: 8 (frecuente)
        """
        try:
            product_ids = self.product_model.search([('sale_ok', '=', True)], limit=50)
            if product_ids:
                self.product_model.read(product_ids, ['name', 'list_price', 'default_code'])
        except Exception as e:
            pass

    @task(5)
    def search_count_partners(self):
        """
        Cuenta partners.
        Peso: 5 (moderado)
        """
        try:
            count = self.partner_model.search_count([])
        except Exception as e:
            pass

    @task(5)
    def read_sale_orders(self):
        """
        Lee órdenes de venta.
        Peso: 5 (moderado)
        """
        try:
            order_ids = self.sale_order_model.search(
                [('state', 'in', ['draft', 'sent', 'sale'])],
                limit=50
            )
            if order_ids:
                self.sale_order_model.read(
                    order_ids,
                    ['name', 'partner_id', 'amount_total', 'state']
                )
        except Exception as e:
            pass

    @task(3)
    def search_partners_with_domain(self):
        """
        Busca partners con dominio específico.
        Peso: 3 (poco frecuente)
        """
        try:
            # Buscar clientes (no compañías) activos
            partner_ids = self.partner_model.search([
                ('is_company', '=', False),
                ('active', '=', True)
            ], limit=30)
            if partner_ids:
                self.partner_model.read(partner_ids, ['name', 'email'])
        except Exception as e:
            pass
