from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    from odoo import fields, models, api

    class ProductProduct(models.Model):
        _inherit = 'product.product'

        warranty_months = fields.Integer(
            string='Warranty (Months)',
            compute='_compute_warranty_months',
            inverse='_inverse_warranty_months',
            store=True,
            readonly=False,
            help="Número de meses de garantía para este producto específico"
        )

        @api.depends('product_tmpl_id.warranty_months')
        def _compute_warranty_months(self):
            for product in self:
                product.warranty_months = product.product_tmpl_id.warranty_months

        def _inverse_warranty_months(self):
            for product in self:
                product.product_tmpl_id.warranty_months = product.warranty_months

