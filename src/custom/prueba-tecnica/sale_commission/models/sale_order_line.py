from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    commission_percent = fields.Float(
        string="Comisión (%)",
        digits=(5, 2),
        compute="_compute_commission_percent",
        store=True,
    )
    commission_amount = fields.Monetary(
        string="Comisión",
        compute="_compute_commission_amount",
        store=True,
    )

    @api.depends("order_id.user_id", "order_id.user_id.commission_percent", "order_id.state")
    def _compute_commission_percent(self):
        for line in self:
            if line.order_id.state != "sale":
                line.commission_percent = 0.0
                continue
            line.commission_percent = line.order_id.user_id.commission_percent

    @api.depends("commission_percent", "price_subtotal")
    def _compute_commission_amount(self):
        for line in self:
            line.commission_amount = line.price_subtotal * line.commission_percent / 100.0
