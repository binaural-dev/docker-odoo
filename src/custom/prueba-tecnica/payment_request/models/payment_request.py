from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# Datos de la solicitud que ya no se pueden cambiar después de enviarla.
LOCKED_FIELDS = {"partner_id", "requester_id", "amount", "currency_id", "date", "concept", "company_id"}
# Estado y datos que registra el sistema: solo cambian a través de los métodos del flujo (_set_state).
FLOW_FIELDS = {"state", "approver_id", "approved_by_id", "approval_date", "rejection_reason", "payment_id"}
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
    approver_id = fields.Many2one(
        "res.users", string="Aprobador asignado", readonly=True, copy=False, tracking=True,
        help="Se asigna al enviar, según el nivel de aprobación que corresponde al monto.",
    )
    approved_by_id = fields.Many2one("res.users", string="Aprobada por", readonly=True, copy=False)
    approval_date = fields.Datetime(string="Fecha de aprobación", readonly=True, copy=False)
    rejection_reason = fields.Text(string="Motivo del rechazo", readonly=True, copy=False)
    payment_id = fields.Many2one("account.payment", string="Pago", readonly=True, copy=False)

    @api.constrains("amount")
    def _check_amount(self):
        for request in self:
            if request.currency_id.compare_amounts(request.amount, 0.0) <= 0:
                raise ValidationError(_("El monto de la solicitud debe ser mayor que cero."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.su and (vals.get("state", "draft") != "draft" or (FLOW_FIELDS - {"state"}) & vals.keys()):
                raise UserError(_("Una solicitud nueva siempre empieza en borrador, sin datos de aprobación ni pago."))
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("payment.request") or "/"
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            if FLOW_FIELDS & vals.keys():
                raise AccessError(_(
                    "El estado y los datos de aprobación y pago solo cambian con los botones del flujo "
                    "(Enviar, Aprobar, Rechazar, Registrar pago)."
                ))
            if LOCKED_FIELDS & vals.keys() and any(request.state != "draft" for request in self):
                raise UserError(_("Una solicitud enviada ya no se puede modificar."))
        return super().write(vals)

    def unlink(self):
        if any(request.state != "draft" for request in self):
            raise UserError(_("Solo se pueden eliminar solicitudes en borrador."))
        return super().unlink()

    # Flujo

    def _check_state_change(self, new_state):
        """Quién puede llevar cada solicitud a new_state. Se llama SIEMPRE antes de _set_state()."""
        self.check_access("write")  # registro visible y editable para este usuario (reglas de registro)
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
            if new_state in ("approved", "rejected"):
                if request.requester_id == self.env.user:
                    raise UserError(_("No puede aprobar ni rechazar su propia solicitud (%s).", request.name))
                if request.approver_id != self.env.user:
                    raise AccessError(_(
                        "La solicitud %(name)s la debe aprobar o rechazar %(approver)s, el aprobador asignado.",
                        name=request.name, approver=request.approver_id.name,
                    ))

    def _set_state(self, vals):
        """Escribe el estado y los datos del flujo, después de _check_state_change().

        sudo() porque write() no deja escribir FLOW_FIELDS a nadie: así ni un write por RPC puede elegir
        el aprobador, aprobar o marcar pagada sin pasar por los métodos. El usuario no cambia (sudo
        conserva el uid), así que el chatter registra a quien hizo el cambio.
        """
        return self.sudo().write(vals)

    def _get_approval_level(self):
        self.ensure_one()
        amount = self.currency_id._convert(self.amount, self.company_id.currency_id, self.company_id, self.date)
        level = self.env["payment.approval.level"].sudo()._find_for(self.company_id, amount)
        if not level:
            raise UserError(_(
                "No hay un nivel de aprobación configurado para el monto de %s. "
                "Pídale a un administrador que lo configure en Solicitudes de pago › Configuración.",
                self.name,
            ))
        if level.approver_id == self.requester_id:
            raise UserError(_(
                "El aprobador de este monto es usted mismo (%s). Pídale a un administrador que asigne otro "
                "aprobador para este nivel.", self.name,
            ))
        return level

    def action_submit(self):
        self._check_state_change("submitted")
        for request in self:
            level = request._get_approval_level()
            request._set_state({"state": "submitted", "approver_id": level.approver_id.id})
            request.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=level.approver_id.id,
                summary=_("Aprobar solicitud de pago %s", request.name),
            )

    def action_approve(self):
        self._check_state_change("approved")
        self._set_state({
            "state": "approved",
            "approved_by_id": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })
        self._close_approval_activity(_("Aprobada"))

    def action_reject(self, reason):
        """Rechaza con un motivo obligatorio que queda en el chatter (lo llama el wizard de rechazo)."""
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Indique el motivo del rechazo."))
        self._check_state_change("rejected")
        self._set_state({"state": "rejected", "rejection_reason": reason})
        self._close_approval_activity(_("Rechazada"))
        for request in self:
            request.message_post(
                body=_("Solicitud rechazada. Motivo: %s", reason),
                partner_ids=request.requester_id.partner_id.ids,
            )

    def _close_approval_activity(self, feedback):
        for request in self:
            request.activity_feedback(
                ["mail.mail_activity_data_todo"], user_id=request.approver_id.id, feedback=feedback,
            )

    def _create_payment(self, journal, payment_date):
        """Crea y publica el pago a proveedor y deja la solicitud en «pagada». Una sola vez por solicitud."""
        self.ensure_one()
        self._check_state_change("paid")
        if self.payment_id:
            raise UserError(_("La solicitud %s ya tiene un pago registrado.", self.name))
        if journal.company_id != self.company_id or journal.type not in ("bank", "cash"):
            raise UserError(_("Elija un diario de banco o efectivo de la compañía %s.", self.company_id.name))
        payment = self.env["account.payment"].create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "journal_id": journal.id,
            "date": payment_date,
            "memo": self.name,
            "company_id": self.company_id.id,
        })
        payment.action_post()
        self._set_state({"state": "paid", "payment_id": payment.id})
        self.message_post(body=Markup(_("Pago registrado: %s")) % payment._get_html_link())
        return payment

    # Botones

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Rechazar solicitud"),
            "res_model": "payment.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_open_payment_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar pago"),
            "res_model": "payment.request.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_view_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
        }
