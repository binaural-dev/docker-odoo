from odoo import fields, models


class StockStorageTagWizard(models.TransientModel):
    _name = 'stock.storage.tag.wizard'
    _description = 'Add Storage Tag Wizard'

    product_ids = fields.Many2many(
        'product.template',
        string='Products',
    )
    tag_ids = fields.Many2many(
        'stock.storage.tag',
        string='Tags to Add',
    )
    remove_tag_ids = fields.Many2many(
        'stock.storage.tag',
        'stock_storage_tag_wizard_remove_rel',
        string='Tags to Remove',
    )

    def action_apply(self):
        for product in self.product_ids:
            if self.tag_ids:
                product.storage_tag_ids = [(4, tag.id) for tag in self.tag_ids]
            if self.remove_tag_ids:
                product.storage_tag_ids = [(3, tag.id) for tag in self.remove_tag_ids]
        return {'type': 'ir.actions.act_window_close'}
