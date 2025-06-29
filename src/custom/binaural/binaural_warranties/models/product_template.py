from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_months = fields.Integer(string="Warranty (Months)")
