from odoo import fields, models


class StockStorageTag(models.Model):
    _name = 'stock.storage.tag'
    _description = 'Storage Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    description = fields.Text(string='Description', translate=True)
    product_ids = fields.Many2many(
        'product.template',
        'product_template_storage_tag_rel',
        'tag_id',
        'product_id',
        string='Products',
    )
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
    )

    def _compute_product_count(self):
        for tag in self:
            tag.product_count = len(tag.product_ids)
