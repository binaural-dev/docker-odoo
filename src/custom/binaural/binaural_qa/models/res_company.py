from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    quality_check_required = fields.Boolean(
        string='Require Quality Check',
        default=False,
    )