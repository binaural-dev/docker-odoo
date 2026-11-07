from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    commission_percent = fields.Float(
        string="Comisión (%)",
        digits=(5, 2),
        readonly=True,
        copy=False,
        help="Se fija al confirmar el pedido, para que la comisión no cambie si después se modifican los porcentajes.",
    )
    commission_amount = fields.Monetary(
        string="Comisión",
        compute="_compute_commission_amount",
        store=True,
    )

    @api.depends("commission_percent", "price_subtotal")
    def _compute_commission_amount(self):
        for line in self:
            line.commission_amount = line.price_subtotal * line.commission_percent / 100.0

    def _get_commission_percent(self):
        """Porcentaje de la categoría del producto (la más específica) o, si no hay, el del vendedor."""
        self.ensure_one()
        rules = self.env["sale.commission.rule"].search([
            ("categ_id", "parent_of", self.product_id.categ_id.id),
            ("company_id", "in", [False, self.company_id.id]),
        ])
        if rules:
            return rules.sorted(lambda r: len(r.categ_id.parent_path or ""), reverse=True)[0].percent
        return self.order_id.user_id.commission_percent
