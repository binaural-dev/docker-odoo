from odoo import api, fields, models


class AccountDiscountRule(models.Model):
    _name = 'account.discount.rule'
    _description = 'Discount Rule'

    name = fields.Char(string='Rule Name', required=True)
    customer_type_id = fields.Many2one(
        'account.customer.type',
        string='Customer Type',
        required=True,
        ondelete='cascade',
    )
    discount_percentage = fields.Float(
        string='Discount (%)',
        default=0.0,
        help='Discount percentage to apply on invoice lines.',
    )
    min_amount = fields.Float(
        string='Minimum Amount',
        default=0.0,
        help='Minimum invoice amount required to apply the discount.',
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('customer_type_uniq', 'unique(customer_type_id)', 'Only one discount rule per customer type is allowed!'),
    ]

    @api.onchange('customer_type_id')
    def _onchange_customer_type_id(self):
        if self.customer_type_id:
            self.name = 'Discount Rule - %s' % self.customer_type_id.name
