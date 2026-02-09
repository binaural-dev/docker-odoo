from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type_id = fields.Many2one(
        'account.customer.type',
        string='Customer Type',
        help='Select the customer type to apply discount rules.',
    )
