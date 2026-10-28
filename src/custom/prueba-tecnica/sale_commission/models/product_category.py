from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    commission_rule_ids = fields.One2many("sale.commission.rule", "categ_id", string="Reglas de comisión")
    commission_percent = fields.Float(
        string="Comisión (%)",
        digits=(5, 2),
        compute="_compute_commission_percent",
        inverse="_inverse_commission_percent",
        groups="sales_team.group_sale_manager",
        help="Si se indica, reemplaza el porcentaje del vendedor para los productos de esta categoría "
             "y de sus subcategorías que no tengan uno propio.",
    )

    def _compute_commission_percent(self):
        for category in self:
            category.commission_percent = category.commission_rule_ids[:1].percent

    def _inverse_commission_percent(self):
        for category in self:
            rule = category.commission_rule_ids[:1]
            if rule:
                rule.percent = category.commission_percent
            elif category.commission_percent:
                self.env["sale.commission.rule"].create({
                    "categ_id": category.id,
                    "percent": category.commission_percent,
                })
