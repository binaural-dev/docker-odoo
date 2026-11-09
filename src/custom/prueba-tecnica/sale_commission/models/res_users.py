from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    commission_percent = fields.Float(
        string="Comisión (%)",
        digits=(5, 2),
        help="Porcentaje del subtotal de cada línea de venta que cobra el vendedor como comisión.",
    )

    @api.constrains("commission_percent")
    def _check_commission_percent(self):
        for user in self:
            if not 0 <= user.commission_percent <= 100:
                raise ValidationError(_("La comisión debe estar entre 0 y 100 %."))
