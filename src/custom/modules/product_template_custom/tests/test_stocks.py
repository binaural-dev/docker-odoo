from odoo.tests.common import TransactionCase

class TestStockAlerts(TransactionCase):

    def setUp(self):
        super(TestStockAlerts, self).setUp()
        
        # 1. Crear producto de prueba con un mínimo de 10
        self.product = self.env['product.template'].create({
            'name': 'Producto Prueba Alerta',
            'type': 'product',
            'minimum_stock_alert': 10.0,
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')

    def test_critical_stock_alert_and_no_duplicates(self):
        """Valida la generación de alertas en mail.message y que no haya duplicados."""
        
        # 2. Ajustar inventario real a 5 unidades (Estado Crítico)
        quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.product_variant_id.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 5.0,
        })
        quant.action_apply_inventory()
        
        # 3. Ejecutar acción automática por primera vez
        self.env['product.template']._cron_check_critical_stock()
        
        # 4. Buscar y validar creación de la alerta
        messages = self.env['mail.message'].search([
            ('model', '=', 'product.template'),
            ('res_id', '=', self.product.id),
            ('body', 'ilike', 'ALERTA:')
        ])
        
        self.assertEqual(len(messages), 1, "Se debe generar exactamente 1 alerta inicial.")
        self.assertTrue(self.product.alert_sent, "El flag alert_sent debe marcarse como True.")
        
        # 5. Ejecutar cron por segunda vez para asegurar la regla anti-spam
        self.env['product.template']._cron_check_critical_stock()
        
        messages_after = self.env['mail.message'].search([
            ('model', '=', 'product.template'),
            ('res_id', '=', self.product.id),
            ('body', 'ilike', 'ALERTA:')
        ])
        
        self.assertEqual(len(messages_after), 1, "No se deben generar alertas duplicadas.")