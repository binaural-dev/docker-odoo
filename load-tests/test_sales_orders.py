# -*- coding: utf-8 -*-
"""
Test específico para módulo Ventas - Gestión de órdenes de venta.

Uso:
    locust -f test_sales_orders.py --host=http://localhost:PORT
"""

from locust import task, between
from base_test import BaseOdooUser


class SalesUser(BaseOdooUser):
    """
    Simula un usuario del departamento de ventas.

    Configuración:
    - Modifica 'instance_name' para apuntar a tu instancia
    - Ajusta 'wait_time' según el comportamiento deseado
    """
    abstract = False
    instance_name = "mercedes"  # <-- CAMBIA ESTO según tu instancia
    wait_time = between(1, 5)

    def on_start(self):
        """Inicializa la conexión y obtiene modelos necesarios."""
        super().on_start()
        self.sale_order_model = self.client.get_model('sale.order')
        self.sale_order_line_model = self.client.get_model('sale.order.line')
        self.partner_model = self.client.get_model('res.partner')
        self.product_model = self.client.get_model('product.product')

    @task(15)
    def read_sale_orders(self):
        """
        Lee órdenes de venta.
        Peso: 15 (muy frecuente)
        """
        try:
            order_ids = self.sale_order_model.search(
                [],
                limit=50,
                order='date_order desc'
            )
            if order_ids:
                self.sale_order_model.read(
                    order_ids,
                    ['name', 'partner_id', 'date_order', 'amount_total',
                     'state', 'user_id', 'invoice_status']
                )
        except Exception as e:
            pass

    @task(10)
    def read_sale_orders_by_state(self):
        """
        Lee órdenes de venta filtradas por estado.
        Peso: 10 (frecuente - vistas filtradas)
        """
        try:
            # Órdenes en estado "Presupuesto enviado"
            order_ids = self.sale_order_model.search(
                [('state', '=', 'sent')],
                limit=30
            )
            if order_ids:
                self.sale_order_model.read(
                    order_ids,
                    ['name', 'partner_id', 'amount_total', 'state']
                )
        except Exception as e:
            pass

    @task(8)
    def read_customers(self):
        """
        Lee clientes (partners).
        Peso: 8 (frecuente)
        """
        try:
            partner_ids = self.partner_model.search(
                [('customer_rank', '>', 0)],
                limit=40
            )
            if partner_ids:
                self.partner_model.read(
                    partner_ids,
                    ['name', 'email', 'phone', 'sale_order_count']
                )
        except Exception as e:
            pass

    @task(5)
    def read_sale_order_lines(self):
        """
        Lee líneas de órdenes de venta.
        Peso: 5 (moderado)
        """
        try:
            line_ids = self.sale_order_line_model.search(
                [],
                limit=50
            )
            if line_ids:
                self.sale_order_line_model.read(
                    line_ids,
                    ['order_id', 'product_id', 'product_uom_qty',
                     'price_unit', 'price_subtotal']
                )
        except Exception as e:
            pass

    @task(5)
    def read_products_catalog(self):
        """
        Lee catálogo de productos.
        Peso: 5 (moderado)
        """
        try:
            product_ids = self.product_model.search(
                [('sale_ok', '=', True), ('active', '=', True)],
                limit=30
            )
            if product_ids:
                self.product_model.read(
                    product_ids,
                    ['name', 'list_price', 'default_code', 'uom_id']
                )
        except Exception as e:
            pass

    @task(3)
    def count_sale_orders_by_month(self):
        """
        Cuenta órdenes agrupadas (simula gráficos).
        Peso: 3 (poco frecuente - dashboards)
        """
        try:
            # Simular consulta de métricas
            states = ['draft', 'sent', 'sale', 'done', 'cancel']
            for state in states:
                count = self.sale_order_model.search_count(
                    [('state', '=', state)]
                )
        except Exception as e:
            pass

    @task(2)
    def search_sale_orders_with_amount(self):
        """
        Busca órdenes con montos específicos.
        Peso: 2 (raro)
        """
        try:
            order_ids = self.sale_order_model.search(
                [('amount_total', '>', 1000)],
                limit=20
            )
            if order_ids:
                self.sale_order_model.read(
                    order_ids,
                    ['name', 'partner_id', 'amount_total', 'state']
                )
        except Exception as e:
            pass
