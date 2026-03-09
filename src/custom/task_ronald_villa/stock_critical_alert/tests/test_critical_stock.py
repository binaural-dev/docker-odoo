from odoo.tests import common

class TestCriticalStock(common.TransactionCase):
    def setUp(self):
        """
        Función de inicialización que se ejecuta antes de cada de test
        """
        super().setUp()
        self.ProductTemplate = self.env['product.template']
        self.Product = self.env['product.product']
        self.Quant = self.env['stock.quant']
        self.Location = self.env['stock.location']
        
        # Crear un producto de prueba estandarizado del tipo 'Almacenable'
        self.product_tmpl = self.ProductTemplate.create({
            'name': 'Test Critical Product',
            'type': 'product',
            'config_min_stock': 10.0,
        })
        self.product = self.product_tmpl.product_variant_id
        
        # Usamos la ubicación por defecto de stock
        self.stock_location = self.env.ref('stock.stock_location_stock')

    def test_01_critical_stock_alert_generated(self):
        """
        Prueba 1: Evalúa la secuencia de movimientos de inventario dinámicos 
        y confirma el registro condicional de alertas en `mail.message`.
        """
        # 1. Ingresar inventario inicial: stock(15) > umbral (10)
        self.Quant._update_available_quantity(self.product, self.stock_location, 15.0)
        self.assertEqual(self.product.qty_available, 15.0, "Stock should be 15")
        self.assertFalse(self.product_tmpl.is_critical_stock, "Should not be critical")
        
        # Conteo previo de mensajes de notificación
        domain = [('res_id', '=', self.product_tmpl.id), ('model', '=', 'product.template'), ('message_type', '=', 'notification')]
        messages_before = self.env['mail.message'].search_count(domain)
        
        # 2. Descontar 10 unds: stock final(5) < umbral (10)
        self.Quant._update_available_quantity(self.product, self.stock_location, -10.0)
        self.assertEqual(self.product.qty_available, 5.0, "Stock should be 5")
        self.assertTrue(self.product_tmpl.is_critical_stock, "Should be marked as critical")
        
        # 3. Comprobar que en efecto el correo o mensaje fue disparado en sistema
        messages_after = self.env['mail.message'].search_count(domain)
        self.assertEqual(messages_after, messages_before + 1, "One new alert message should be generated")
        
        # 4. Descontar aún más stock; probamos que NO se cree otro mensaje nuevo basura
        self.Quant._update_available_quantity(self.product, self.stock_location, -2.0)
        self.assertEqual(self.product.qty_available, 3.0, "Stock should be 3")
        messages_after_second_drop = self.env['mail.message'].search_count(domain)
        self.assertEqual(messages_after_second_drop, messages_after, "No duplicate message should be generated")
        
        # 5. Volver a abastecer inventario en positivo
        self.Quant._update_available_quantity(self.product, self.stock_location, 10.0)
        self.assertEqual(self.product.qty_available, 13.0, "Stock should be 13")
        self.assertFalse(self.product_tmpl.is_critical_stock, "Should no longer be critical")
        
        # 6. Descontarlo de nuevo abajo del límite confirmando regeneración limpia posterior
        self.Quant._update_available_quantity(self.product, self.stock_location, -5.0)
        self.assertTrue(self.product_tmpl.is_critical_stock, "Should be marked as critical again")
        messages_final = self.env['mail.message'].search_count(domain)
        self.assertEqual(messages_final, messages_after_second_drop + 1, "Another alert should be generated")

    def test_02_config_change_triggers_alert(self):
        """
        Prueba 2: Evalúa que actualizar el límite desde la propia vista del registro 
        verifique el estado en tiempo real, incluso sin movimientos de existencias.
        """
        # Seteamos el estado actual por encima de config_min_stock(10.0)
        self.Quant._update_available_quantity(self.product, self.stock_location, 15.0)
        self.assertEqual(self.product.qty_available, 15.0, "Stock should be 15")
        
        # Al nacer el template validamos que es False el estado en Alerta
        self.assertFalse(self.product_tmpl.is_critical_stock, "Should not be critical")
        
        domain = [('res_id', '=', self.product_tmpl.id), ('model', '=', 'product.template'), ('message_type', '=', 'notification')]
        messages_before = self.env['mail.message'].search_count(domain)
        
        # Subimos la barrera hasta 20 (lo cual hace el stock(15) "Crítico" instantáneamente)
        self.product_tmpl.write({'config_min_stock': 20.0})
        
        self.assertTrue(self.product_tmpl.is_critical_stock, "Should be marked as critical after config change")
        
        messages_after = self.env['mail.message'].search_count(domain)
        self.assertEqual(messages_after, messages_before + 1, "Alert message should be generated on config change")
        
        # Devolvemos la barrera la cantidad original
        self.product_tmpl.write({'config_min_stock': 10.0})
        
        self.assertFalse(self.product_tmpl.is_critical_stock, "Should no longer be critical after config change")
