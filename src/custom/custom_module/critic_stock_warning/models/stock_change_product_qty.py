from odoo import _, fields, models, api
import logging
_logger = logging.getLogger(__name__)

class StockChangeProductQty(models.TransientModel):

    _inherit = 'stock.change.product.qty'


    def change_product_qty(self):
        res = super().change_product_qty()
        self.env['product.template'].search([('id', '=', self.product_id.id)]).check_for_critical_qty()
        return res