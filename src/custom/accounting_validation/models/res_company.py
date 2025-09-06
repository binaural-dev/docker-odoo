from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    payment_validation_limit = fields.Float(string='Límite para Doble Validación', default=10000.0, help='Monto a partir del cual se requiere doble validación para pagos')