from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warranty_months = fields.Integer(string='Warranty', default=0, store=True)

    @api.onchange('product_id')
    def _onchange_product_id_warranty(self):
        if self.product_id:
            self.warranty_months = self.product_id.warranty_months