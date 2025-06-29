import unittest

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TaxClassificationDefaultValue(TransactionCase):

    def setUp(self):
        super(TaxClassificationDefaultValue, self).setUp()

        # Configuración inicial
        self.company = self.env.user.company_id
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'service',
        })

        self.invoice_vals = {
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })]
        }

    def test_default_value_on_invoice_creation(self):
        invoice = self.env['account.move'].create(self.invoice_vals)
        self.assertEqual(
            invoice.tax_classification,
            'A',
            "Default value for tax_classification should be 'A'"
        )

    def test_manual_value_persistence(self):
        # Crear factura con valor explícito
        vals = self.invoice_vals.copy()
        vals['tax_classification'] = 'B'
        invoice = self.env['account.move'].create(vals)

        # Verificar que se guardó el valor manual
        self.assertEqual(
            invoice.tax_classification,
            'B',
            "The value of tax_classification should be 'B' when manually set"
        )
