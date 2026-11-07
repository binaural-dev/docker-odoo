from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentApprovalLevel(models.Model):
    _name = "payment.approval.level"
    _description = "Nivel de Aprobación de Solicitudes de Pago"
    _order = "amount_min desc, sequence, id"

    name = fields.Char(string="Nombre del Nivel", required=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    amount_min = fields.Monetary(
        string="Monto Mínimo",
        required=True,
        currency_field="currency_id",
        help="Monto a partir del cual se requiere la aprobación de este nivel.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    approver_id = fields.Many2one(
        "res.users",
        string="Aprobador",
        required=True,
        domain="[('share', '=', False)]",
        help="Usuario responsable de aprobar las solicitudes en este rango.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("check_amount_min", "CHECK(amount_min >= 0)", "El monto mínimo no puede ser negativo."),
    ]

    @api.constrains("amount_min")
    def _check_amount_min(self):
        for level in self:
            if level.amount_min < 0:
                raise ValidationError(_("El monto mínimo del nivel de aprobación no puede ser negativo."))

