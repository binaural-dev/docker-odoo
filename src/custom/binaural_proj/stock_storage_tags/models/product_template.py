from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    storage_tag_ids = fields.Many2many(
        'stock.storage.tag',
        'product_template_storage_tag_rel',
        'product_id',
        'tag_id',
        string='Storage Tags',
    )
