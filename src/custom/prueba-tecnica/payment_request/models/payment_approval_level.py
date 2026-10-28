from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentApprovalLevel(models.Model):
    _name = "payment.approval.level"
    _description = "Nivel de aprobación de solicitudes de pago"
    _order = "company_id, min_amount"
    _rec_name = "approver_id"

    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", string="Moneda")
    min_amount = fields.Monetary(
        string="Desde (monto)", required=True, currency_field="currency_id",
        help="Las solicitudes desde este monto (en la moneda de la compañía) las aprueba este aprobador, "
             "hasta el monto del siguiente nivel.",
    )
    approver_id = fields.Many2one(
        "res.users", string="Aprobador", required=True,
        domain=lambda self: [("groups_id", "in", self.env.ref("payment_request.group_payment_request_approver").id)],
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("min_amount_company_uniq", "unique(company_id, min_amount)",
         "Ya existe un nivel con ese monto para esta compañía."),
    ]

    @api.constrains("min_amount")
    def _check_min_amount(self):
        for level in self:
            if level.min_amount < 0:
                raise ValidationError(_("El monto del nivel no puede ser negativo."))

    @api.constrains("approver_id")
    def _check_approver_group(self):
        for level in self:
            if not level.approver_id.has_group("payment_request.group_payment_request_approver"):
                raise ValidationError(_(
                    "%s no tiene el grupo Aprobador de solicitudes de pago.", level.approver_id.name,
                ))

    @api.model
    def _find_for(self, company, amount):
        """Nivel que corresponde a un monto (en la moneda de la compañía): el de mayor monto mínimo que no lo supere."""
        return self.search(
            [("company_id", "=", company.id), ("min_amount", "<=", amount)],
            order="min_amount desc", limit=1,
        )
