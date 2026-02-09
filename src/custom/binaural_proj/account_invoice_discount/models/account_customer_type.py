from odoo import fields, models


class AccountCustomerType(models.Model):
    _name = 'account.customer.type'
    _description = 'Customer Type'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    discount_rule_id = fields.One2many(
        'account.discount.rule',
        'customer_type_id',
        string='Discount Rule',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The code must be unique per company!'),
    ]
