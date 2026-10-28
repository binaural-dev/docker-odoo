from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# Datos de la solicitud que el solicitante ya no puede cambiar después de enviarla.
LOCKED_FIELDS = {"partner_id", "requester_id", "amount", "currency_id", "date", "concept", "company_id"}
# Solo se escriben junto con la aprobación (action_approve).
APPROVAL_FIELDS = {"approved_by_id", "approval_date"}
# Estado actual -> estados a los que se puede pasar.
STATE_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"approved", "rejected"},
    "approved": {"paid"},
}
# Estado destino -> grupo que puede llevar la solicitud a ese estado.
STATE_GROUPS = {
    "approved": "payment_request.group_payment_request_approver",
    "rejected": "payment_request.group_payment_request_approver",
    "paid": "payment_request.group_payment_request_treasury",
}


class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "Solicitud de pago"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Número", required=True, copy=False, readonly=True, default="/")
    partner_id = fields.Many2one(
        "res.partner", string="Proveedor", required=True, tracking=True, check_company=True,
    )
    requester_id = fields.Many2one(
        "res.users", string="Solicitante", required=True, readonly=True, tracking=True,
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Moneda", required=True, tracking=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount = fields.Monetary(string="Monto", required=True, tracking=True, currency_field="currency_id")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today, tracking=True)
    concept = fields.Text(string="Concepto", required=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("submitted", "Enviada"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado", required=True, default="draft", readonly=True, copy=False, tracking=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Aprobada por", readonly=True, copy=False)
    approval_date = fields.Datetime(string="Fecha de aprobación", readonly=True, copy=False)

    @api.constrains("amount")
    def _check_amount(self):
        for request in self:
            if request.currency_id.compare_amounts(request.amount, 0.0) <= 0:
                raise ValidationError(_("El monto de la solicitud debe ser mayor que cero."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.su and vals.get("state", "draft") != "draft":
                raise UserError(_("Una solicitud nueva siempre empieza en borrador."))
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("payment.request") or "/"
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            if LOCKED_FIELDS & vals.keys() and any(request.state != "draft" for request in self):
                raise UserError(_("Una solicitud enviada ya no se puede modificar."))
            if APPROVAL_FIELDS & vals.keys() and vals.get("state") != "approved":
                raise UserError(_("Los datos de la aprobación solo se registran al aprobar."))
            if "state" in vals:
                self._check_state_change(vals["state"])
        return super().write(vals)

    def _check_state_change(self, new_state):
        """Valida la transición de estado para el usuario actual (botón, método o write directo)."""
        group = STATE_GROUPS.get(new_state)
        if group and not self.env.user.has_group(group):
            raise AccessError(_("No tiene permiso para dejar la solicitud en ese estado."))
        for request in self:
            if new_state not in STATE_TRANSITIONS.get(request.state, set()):
                raise UserError(_(
                    "La solicitud %(name)s no puede pasar de «%(old)s» a «%(new)s».",
                    name=request.name,
                    old=dict(self._fields["state"].selection)[request.state],
                    new=dict(self._fields["state"].selection)[new_state],
                ))
            if new_state in ("approved", "rejected") and request.requester_id == self.env.user:
                raise UserError(_("No puede aprobar ni rechazar su propia solicitud (%s).", request.name))

    def unlink(self):
        if any(request.state != "draft" for request in self):
            raise UserError(_("Solo se pueden eliminar solicitudes en borrador."))
        return super().unlink()

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write({
            "state": "approved",
            "approved_by_id": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_mark_paid(self):
        self.write({"state": "paid"})
