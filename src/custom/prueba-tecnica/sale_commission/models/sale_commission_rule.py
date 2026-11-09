from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleCommissionRule(models.Model):
    _name = "sale.commission.rule"
    _description = "Comisión por categoría de producto"
    _rec_name = "categ_id"

    categ_id = fields.Many2one("product.category", string="Categoría", required=True, ondelete="cascade")
    percent = fields.Float(string="Comisión (%)", digits=(5, 2), required=True)
    company_id = fields.Many2one("res.company", string="Compañía")

    @api.constrains("percent")
    def _check_percent(self):
        for rule in self:
            if not 0 <= rule.percent <= 100:
                raise ValidationError(_("La comisión debe estar entre 0 y 100 %."))
