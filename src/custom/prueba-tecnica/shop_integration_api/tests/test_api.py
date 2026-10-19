import json
from datetime import datetime, timedelta
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestShopIntegrationApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_user = cls.env['res.users'].create({
            'name': 'API Test User',
            'login': 'api_user_test',
            'password': 'Password123!',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('sales_team.group_sale_salesman').id),
                (4, cls.env.ref('stock.group_stock_user').id),
            ],
        })

        user = cls.api_user.with_user(cls.api_user)
        key_expiration = datetime.now() + timedelta(days=30)
        cls.api_key = user.env['res.users.apikeys']._generate('rpc', 'Test Key API', key_expiration)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente Tienda C.A.',
            'vat': 'J-99999999-0',
        })

        cls.cat_electronics = cls.env['product.category'].create({'name': 'Electronics'})
        cls.cat_clothes = cls.env['product.category'].create({'name': 'Clothes'})

        cls.prod_active_stock = cls.env['product.product'].create({
            'name': 'Laptop Pro',
            'default_code': 'LAP-001',
            'list_price': 1200.0,
            'categ_id': cls.cat_electronics.id,
            'sale_ok': True,
            'is_storable': True,
        })
        cls.prod_no_stock = cls.env['product.product'].create({
            'name': 'Teclado Mecanico',
            'default_code': 'KB-001',
            'list_price': 80.0,
            'categ_id': cls.cat_electronics.id,
            'sale_ok': True,
            'is_storable': True,
        })
        cls.prod_no_sale = cls.env['product.product'].create({
            'name': 'Repuesto Interno',
            'default_code': 'REP-999',
            'list_price': 50.0,
            'categ_id': cls.cat_electronics.id,
            'sale_ok': False,
            'is_storable': True,
        })

        warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        if warehouse:
            cls.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': cls.prod_active_stock.id,
                'location_id': warehouse.lot_stock_id.id,
                'inventory_quantity': 15,
            }).action_apply_inventory()

    def setUp(self):
        super().setUp()
        self.authenticate('api_user_test', 'Password123!')

    def test_get_products_all(self):
        res = self.url_open('/api/v1/products')
        self.assertEqual(res.status_code, 200)
        ids = [item['id'] for item in res.json()]
        self.assertIn(self.prod_active_stock.id, ids)
        self.assertNotIn(self.prod_no_sale.id, ids)

    def test_filter_category(self):
        res = self.url_open(f'/api/v1/products?category_id={self.cat_electronics.id}')
        self.assertEqual(res.status_code, 200)
        ids = [item['id'] for item in res.json()]
        self.assertIn(self.prod_active_stock.id, ids)

    def test_filter_only_stock(self):
        res = self.url_open('/api/v1/products?only_stock=true')
        self.assertEqual(res.status_code, 200)
        ids = [item['id'] for item in res.json()]
        self.assertIn(self.prod_active_stock.id, ids)
        self.assertNotIn(self.prod_no_stock.id, ids)

    def test_filter_modified_since(self):
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        res = self.url_open(f'/api/v1/products?modified_since={past_date}')
        self.assertEqual(res.status_code, 200)

    def test_invalid_date_format_returns_400_not_500(self):
        res = self.url_open('/api/v1/products?modified_since=fecha-invalida')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'INVALID_DATE_FORMAT')

    def test_post_order_auth_fail(self):
        """Sin clave o con clave inválida devuelve 401."""
        res = self.url_open('/api/v1/orders', data=json.dumps({}), headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 401)

        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer clave_falsa_123'}
        res = self.url_open('/api/v1/orders', data=json.dumps({}), headers=headers)
        self.assertEqual(res.status_code, 401)

    def test_post_order_validation_errors(self):
        """Valida que RIF, producto inexistente o cantidad <= 0 devuelvan HTTP 422 con campo exacto."""
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'}

        payload = {'rif': 'J-00000000-0', 'lines': [{'default_code': 'LAP-001', 'quantity': 1}]}
        res = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()['error']['code'], 'PARTNER_NOT_FOUND')
        self.assertEqual(res.json()['error']['field'], 'rif')

        payload = {'rif': 'J-99999999-0', 'lines': [{'default_code': 'NO-EXISTE', 'quantity': 1}]}
        res = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()['error']['code'], 'PRODUCT_NOT_FOUND')
        self.assertEqual(res.json()['error']['field'], 'lines[0].default_code')

        payload = {'rif': 'J-99999999-0', 'lines': [{'default_code': 'LAP-001', 'quantity': 0}]}
        res = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()['error']['code'], 'INVALID_QUANTITY')
        self.assertEqual(res.json()['error']['field'], 'lines[0].quantity')

    def test_post_order_success_and_logging(self):
        """Creación exitosa de pedido y verificación del modelo de log."""
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'}
        payload = {
            'rif': 'J-99999999-0',
            'client_order_ref': 'PED-EXT-001',
            'lines': [{'default_code': 'LAP-001', 'quantity': 2}]
        }
        res = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn('order_id', data)

        log = self.env['shop.api.log'].sudo().search([('endpoint', '=', '/api/v1/orders')], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.response_code, 201)
        self.assertEqual(log.user_id.id, self.api_user.id)

    def test_post_order_idempotency(self):
        """Misma clave y contenido devuelve mismo pedido. Misma clave y otro contenido devuelve 409."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Idempotency-Key': 'IDEMP-TEST-KEY-001',
        }
        payload = {
            'rif': 'J-99999999-0',
            'client_order_ref': 'PED-IDEMP-01',
            'lines': [{'default_code': 'LAP-001', 'quantity': 1}]
        }
        res1 = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res1.status_code, 201)
        order_id = res1.json()['order_id']

        res2 = self.url_open('/api/v1/orders', data=json.dumps(payload), headers=headers)
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json()['order_id'], order_id)

        payload_diff = dict(payload, client_order_ref='PED-OTRO-CONTENIDO')
        res3 = self.url_open('/api/v1/orders', data=json.dumps(payload_diff), headers=headers)
        self.assertEqual(res3.status_code, 409)
        self.assertEqual(res3.json()['error']['code'], 'IDEMPOTENCY_CONFLICT')