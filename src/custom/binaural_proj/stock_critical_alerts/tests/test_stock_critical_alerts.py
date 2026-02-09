from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockCriticalAlerts(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductTemplate = cls.env['product.template']
        cls.StockQuant = cls.env['stock.quant']
        cls.stock_location = cls.env.ref('stock.stock_location_stock')

        cls.category_electronics = cls.env['product.category'].create({
            'name': 'Electronics',
        })
        cls.category_food = cls.env['product.category'].create({
            'name': 'Food',
        })

        cls.product_a = cls.ProductTemplate.create({
            'name': 'Test Product A',
            'type': 'product',
            'stock_minimum': 10.0,
            'categ_id': cls.category_electronics.id,
        })
        cls.product_b = cls.ProductTemplate.create({
            'name': 'Test Product B',
            'type': 'product',
            'stock_minimum': 5.0,
            'categ_id': cls.category_food.id,
        })
        cls.product_no_minimum = cls.ProductTemplate.create({
            'name': 'Test Product No Minimum',
            'type': 'product',
            'stock_minimum': 0.0,
        })
        cls.product_consumable = cls.ProductTemplate.create({
            'name': 'Test Consumable',
            'type': 'consu',
            'stock_minimum': 10.0,
        })

    def _update_product_qty(self, product, qty):
        product_product = product.product_variant_id
        self.StockQuant.with_context(inventory_mode=True).create({
            'product_id': product_product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': qty,
        }).action_apply_inventory()

    def test_01_stock_minimum_field_exists(self):
        self.assertTrue(hasattr(self.product_a, 'stock_minimum'))
        self.assertEqual(self.product_a.stock_minimum, 10.0)
        self.assertEqual(self.product_b.stock_minimum, 5.0)
        self.assertEqual(self.product_no_minimum.stock_minimum, 0.0)

    def test_02_stock_alert_sent_field_exists(self):
        self.assertTrue(hasattr(self.product_a, 'stock_alert_sent'))
        self.assertFalse(self.product_a.stock_alert_sent)

    def test_03_alert_generated_when_stock_below_minimum(self):
        self._update_product_qty(self.product_a, 5.0)

        initial_message_count = len(self.product_a.message_ids)

        self.product_a._check_stock_critical()

        self.assertTrue(self.product_a.stock_alert_sent)
        self.assertGreater(len(self.product_a.message_ids), initial_message_count)

        last_message = self.product_a.message_ids[0]
        self.assertIn('Critical Stock Alert', last_message.body)

    def test_04_no_alert_when_stock_above_minimum(self):
        self._update_product_qty(self.product_a, 15.0)

        initial_message_count = len(self.product_a.message_ids)

        self.product_a._check_stock_critical()

        self.assertFalse(self.product_a.stock_alert_sent)
        self.assertEqual(len(self.product_a.message_ids), initial_message_count)

    def test_05_no_duplicate_alerts(self):
        self._update_product_qty(self.product_b, 2.0)

        self.product_b._check_stock_critical()
        first_message_count = len(self.product_b.message_ids)
        self.assertTrue(self.product_b.stock_alert_sent)

        self.product_b._check_stock_critical()
        self.product_b._check_stock_critical()
        self.product_b._check_stock_critical()

        self.assertEqual(len(self.product_b.message_ids), first_message_count)

    def test_06_alert_reset_when_stock_restored(self):
        self._update_product_qty(self.product_a, 3.0)
        self.product_a._check_stock_critical()
        self.assertTrue(self.product_a.stock_alert_sent)

        self._update_product_qty(self.product_a, 15.0)
        self.product_a._check_stock_critical()
        self.assertFalse(self.product_a.stock_alert_sent)

        self._update_product_qty(self.product_a, 3.0)
        initial_message_count = len(self.product_a.message_ids)
        self.product_a._check_stock_critical()
        self.assertTrue(self.product_a.stock_alert_sent)
        self.assertGreater(len(self.product_a.message_ids), initial_message_count)

    def test_07_no_alert_for_zero_minimum(self):
        self._update_product_qty(self.product_no_minimum, 0.0)

        initial_message_count = len(self.product_no_minimum.message_ids)
        self.product_no_minimum._check_stock_critical()

        self.assertFalse(self.product_no_minimum.stock_alert_sent)
        self.assertEqual(len(self.product_no_minimum.message_ids), initial_message_count)

    def test_08_no_alert_for_consumable_products(self):
        initial_message_count = len(self.product_consumable.message_ids)
        self.product_consumable._check_stock_critical()

        self.assertFalse(self.product_consumable.stock_alert_sent)
        self.assertEqual(len(self.product_consumable.message_ids), initial_message_count)

    def test_09_cron_method_exists(self):
        self.assertTrue(hasattr(self.ProductTemplate, '_cron_check_stock_critical'))
        self.ProductTemplate._cron_check_stock_critical()

    def test_10_dashboard_action_exists(self):
        action = self.env.ref(
            'stock_critical_alerts.action_product_critical_stock',
            raise_if_not_found=False
        )
        self.assertTrue(action)
        self.assertEqual(action.res_model, 'product.template')
        self.assertIn('kanban', action.view_mode)
        self.assertIn('tree', action.view_mode)

    def test_11_dashboard_views_exist(self):
        kanban_view = self.env.ref(
            'stock_critical_alerts.product_template_critical_stock_kanban',
            raise_if_not_found=False
        )
        tree_view = self.env.ref(
            'stock_critical_alerts.product_template_critical_stock_tree',
            raise_if_not_found=False
        )
        self.assertTrue(kanban_view)
        self.assertTrue(tree_view)
        self.assertEqual(kanban_view.model, 'product.template')
        self.assertEqual(tree_view.model, 'product.template')

    def test_12_dashboard_groups_by_category(self):
        action = self.env.ref('stock_critical_alerts.action_product_critical_stock')
        context = action.context
        self.assertIn('group_by', context)
        self.assertIn('categ_id', context)
