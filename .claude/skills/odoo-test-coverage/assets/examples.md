# Ejemplos de tests unitarios Odoo

## 1. Test básico de modelo

```python
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('binaural_contact', 'res_partner', '-at_install', 'post_install')
class TestResPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'vat': '12345678',
        })

    def test_create_partner(self):
        self.assertTrue(self.partner.id)
        self.assertEqual(self.partner.name, 'Test Partner')

    def test_vat_validation_raises(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({'name': 'Bad', 'vat': 'INVALID'})
```

## 2. Test con Form

```python
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged('binaural_sale', 'sale_order', '-at_install', 'post_install')
class TestSaleOrder(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
            'list_price': 100,
        })

    def test_sale_order_form(self):
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner
            with so_form.order_line.new() as line:
                line.product_id = self.product
                line.product_uom_qty = 2
        so = so_form.save()
        self.assertEqual(len(so.order_line), 1)
```

## 3. Test de controlador con mock

```python
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged


@tagged('binaural_unidigital', 'controller', '-at_install', 'post_install')
class TestController(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Test Co'})

    @patch('odoo.addons.binaural_unidigital.controllers.create_invoice.requests.post')
    def test_api_call(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'result': 'ok'}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = self.env['account.move'].sync_single_invoice()
        self.assertTrue(result)
```

## 4. Test de wizard

```python
from odoo.tests.common import TransactionCase, tagged
from odoo.tests import Form


@tagged('binaural_payment_extension', 'wizard_retention_iva', '-at_install', 'post_install')
class TestWizardRetentionIva(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

    def test_wizard_action(self):
        wizard = self.env['wizard.retention.iva'].create({
            'partner_id': self.partner.id,
        })
        result = wizard.action_generate()
        self.assertTrue(result)
```
