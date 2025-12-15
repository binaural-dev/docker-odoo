from odoo import _, fields, models, api
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):

    _inherit = 'stock.picking'


    def button_validate(self):
        res = super().button_validate()
        self.env['product.template'].search([('id', '=', self.product_id.id)]).check_for_critical_qty()
        return res