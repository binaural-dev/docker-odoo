from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install', 'payment_validation')
class TestPaymentDoubleValidation(TransactionCase):

    def setUp(self):
        super(TestPaymentDoubleValidation, self).setUp()
        self.Payment = self.env['account.payment']
        self.company = self.env.company
        self.company.payment_validation_limit = 5000.0
        
        # Crear partner y journal para pruebas
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.journal = self.env['account.journal'].create({
            'name': 'Test Bank',
            'type': 'bank',
            'code': 'TEST'
        })

    def test_payment_below_limit_no_validation(self):
        """Test pago por debajo del límite no requiere validación"""
        payment = self.Payment.create({
            'amount': 4000.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })
        payment.action_post()
        self.assertEqual(payment.state, 'posted')
        self.assertFalse(payment.finance_validation)

    def test_payment_above_limit_requires_validation(self):
        """Test pago por encima del límite requiere validación"""
        payment = self.Payment.create({
            'amount': 6000.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })
        
        # Debería fallar al intentar publicar sin validación
        with self.assertRaises(UserError):
            payment.action_post()

    def test_payment_above_limit_with_validation(self):
        """Test pago por encima del límite con validación exitosa"""
        payment = self.Payment.create({
            'amount': 6000.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'finance_validation': True,
        })
        
        # Debería publicarse correctamente
        payment.action_post()
        self.assertEqual(payment.state, 'posted')
        self.assertTrue(payment.finance_validation)

    def test_validation_button(self):
        """Test botón de validación de finanzas"""
        payment = self.Payment.create({
            'amount': 6000.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })
        
        # Validar mediante el botón
        payment.action_validate_finance()
        self.assertTrue(payment.finance_validation)

    def test_company_limit_zero(self):
        """Test con límite en cero (no debe requerir validación)"""
        self.company.payment_validation_limit = 0.0
        
        payment = self.Payment.create({
            'amount': 100000.0,  # Monto muy alto
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })
        
        # Debería publicarse sin problemas
        payment.action_post()
        self.assertEqual(payment.state, 'posted')