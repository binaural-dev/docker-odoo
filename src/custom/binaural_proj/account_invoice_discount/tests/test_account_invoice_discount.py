from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestAccountInvoiceDiscount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AccountMove = cls.env['account.move']
        cls.AccountMoveLine = cls.env['account.move.line']
        cls.Partner = cls.env['res.partner']
        cls.CustomerType = cls.env['account.customer.type']
        cls.DiscountRule = cls.env['account.discount.rule']
        cls.Product = cls.env['product.product']

        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)

        if not cls.income_account:
            cls.income_account = cls.env['account.account'].create({
                'name': 'Test Income',
                'code': 'TEST_INC',
                'account_type': 'income',
            })

        cls.customer_type_vip = cls.CustomerType.create({
            'name': 'VIP',
            'code': 'VIP',
        })
        cls.customer_type_retail = cls.CustomerType.create({
            'name': 'Retail',
            'code': 'RETAIL',
        })

        cls.discount_rule_vip = cls.DiscountRule.create({
            'name': 'VIP Discount 15%',
            'customer_type_id': cls.customer_type_vip.id,
            'discount_percentage': 15.0,
            'min_amount': 100.0,
        })

        cls.partner_vip = cls.Partner.create({
            'name': 'VIP Customer',
            'customer_type_id': cls.customer_type_vip.id,
        })
        cls.partner_retail = cls.Partner.create({
            'name': 'Retail Customer',
            'customer_type_id': cls.customer_type_retail.id,
        })
        cls.partner_no_type = cls.Partner.create({
            'name': 'Regular Customer',
        })

        cls.product = cls.Product.create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 50.0,
        })

    def _create_invoice(self, partner, lines_data):
        invoice = self.AccountMove.create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': line['qty'],
                    'price_unit': line['price'],
                    'account_id': self.income_account.id,
                }) for line in lines_data
            ],
        })
        return invoice

    def test_01_customer_type_model_exists(self):
        self.assertTrue('account.customer.type' in self.env)
        self.assertTrue(self.customer_type_vip.exists())
        self.assertEqual(self.customer_type_vip.name, 'VIP')
        self.assertEqual(self.customer_type_vip.code, 'VIP')

    def test_02_discount_rule_model_exists(self):
        self.assertTrue('account.discount.rule' in self.env)
        self.assertTrue(self.discount_rule_vip.exists())
        self.assertEqual(self.discount_rule_vip.discount_percentage, 15.0)
        self.assertEqual(self.discount_rule_vip.min_amount, 100.0)

    def test_03_partner_customer_type_field_exists(self):
        self.assertIn('customer_type_id', self.Partner._fields)
        self.assertEqual(self.partner_vip.customer_type_id, self.customer_type_vip)

    def test_04_discount_applied_on_validation_above_min_amount(self):
        invoice = self._create_invoice(self.partner_vip, [
            {'qty': 3, 'price': 50.0},
        ])
        invoice.action_post()

        for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
            self.assertEqual(line.discount, 15.0)

    def test_05_no_discount_below_min_amount(self):
        invoice = self._create_invoice(self.partner_vip, [
            {'qty': 1, 'price': 50.0},
        ])
        invoice.action_post()

        for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
            self.assertEqual(line.discount, 0.0)

    def test_06_no_discount_without_customer_type(self):
        invoice = self._create_invoice(self.partner_no_type, [
            {'qty': 5, 'price': 100.0},
        ])
        invoice.action_post()

        for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
            self.assertEqual(line.discount, 0.0)

    def test_07_no_discount_without_rule(self):
        invoice = self._create_invoice(self.partner_retail, [
            {'qty': 5, 'price': 100.0},
        ])
        invoice.action_post()

        for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
            self.assertEqual(line.discount, 0.0)

    def test_08_discount_rule_unique_per_customer_type(self):
        constraints = [c[0] for c in self.DiscountRule._sql_constraints]
        self.assertIn('customer_type_uniq', constraints)

    def test_09_menu_action_exists(self):
        action_types = self.env.ref(
            'account_invoice_discount.action_account_customer_type',
            raise_if_not_found=False
        )
        action_rules = self.env.ref(
            'account_invoice_discount.action_account_discount_rule',
            raise_if_not_found=False
        )
        self.assertTrue(action_types)
        self.assertTrue(action_rules)

    def test_10_discount_zero_min_amount_always_applies(self):
        self.DiscountRule.create({
            'name': 'Retail Discount 5%',
            'customer_type_id': self.customer_type_retail.id,
            'discount_percentage': 5.0,
            'min_amount': 0.0,
        })

        invoice = self._create_invoice(self.partner_retail, [
            {'qty': 1, 'price': 10.0},
        ])
        invoice.action_post()

        for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
            self.assertEqual(line.discount, 5.0)
