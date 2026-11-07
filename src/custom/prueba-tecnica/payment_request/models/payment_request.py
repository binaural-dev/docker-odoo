from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "Solicitud de Pago a Proveedor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Número", required=True, copy=False, readonly=True, default="/")
    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        required=True,
        tracking=True,
    )
    applicant_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    approver_id = fields.Many2one(
        "res.users",
        string="Aprobador Asignado",
        readonly=True,
        tracking=True,
        copy=False,
        help="Usuario aprobador asignado según el nivel de aprobación correspondiente al monto.",
    )
    approver_user_id = fields.Many2one(
        "res.users",
        string="Aprobado por",
        readonly=True,
        copy=False,
        help="Usuario que efectivamente aprobó la solicitud.",
    )
    approval_date = fields.Datetime(
        string="Fecha de Aprobación",
        readonly=True,
        copy=False,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago Contable",
        readonly=True,
        copy=False,
        help="Asiento contable de pago generado por tesorería.",
    )
    payment_amount = fields.Monetary(
        string="Monto Pagado",
        related="payment_id.amount",
        readonly=True,
        currency_field="payment_currency_id",
        help="Monto efectivamente registrado en el asiento contable de pago.",
    )
    payment_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de Pago",
        related="payment_id.currency_id",
        readonly=True,
    )
    amount = fields.Monetary(
        string="Monto",
        required=True,
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    concept = fields.Char(
        string="Concepto",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("sent", "Enviada"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    reject_reason = fields.Text(string="Motivo de rechazo", tracking=True, copy=False)

    _sql_constraints = [
        ("name_uniq", "unique(name, company_id)", "El número de la solicitud de pago debe ser único."),
    ]

    @api.constrains("amount")
    def _check_amount(self):
        for request in self:
            if request.amount <= 0:
                raise ValidationError(_("El monto de la solicitud debe ser estrictamente mayor a cero."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                seq_code = "payment.request"
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = self.env["ir.sequence"].with_company(company_id).next_by_code(seq_code) or "/"
        return super().create(vals_list)

    def action_send(self):
        for request in self:
            if request.state != "draft":
                raise UserError(_("Solo se pueden enviar solicitudes en estado Borrador."))

            # Asignar aprobador según el nivel de aprobación configurado
            level = self.env["payment.approval.level"].search(
                [
                    ("company_id", "=", request.company_id.id),
                    ("amount_min", "<=", request.amount),
                ],
                order="amount_min desc, sequence, id",
                limit=1,
            )
            if not level:
                raise UserError(
                    _(
                        "No existe un nivel de aprobación configurado para el monto %s %s en la compañía %s."
                    )
                    % (request.amount, request.currency_id.symbol, request.company_id.name)
                )

            request.approver_id = level.approver_id

            # Programar actividad para el aprobador asignado
            request.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=request.approver_id.id,
                summary=_("Solicitud de pago pendiente de aprobación"),
                note=_(
                    "Solicitud de pago %s por %s %s para %s"
                )
                % (request.name, request.amount, request.currency_id.symbol, request.partner_id.name),
            )

        self.write({"state": "sent"})

    def action_approve(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios con permisos de Aprobador pueden aprobar solicitudes de pago."))

        # Bloqueo a nivel de base de datos para prevenir condiciones de carrera (FOR UPDATE NOWAIT)
        try:
            self.env.cr.execute(
                "SELECT id, state FROM payment_request WHERE id IN %s FOR UPDATE NOWAIT",
                [tuple(self.ids)],
            )
        except Exception:
            raise UserError(
                _("La solicitud está siendo procesada concurrentemente por otro aprobador. Por favor, recargue la página.")
            )

        # Invalidar caché local para asegurar lectura del estado actualizado desde la BD bajo el bloqueo
        self.invalidate_recordset(["state", "approver_id"])

        for request in self:
            if request.state != "sent":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado 'Enviada'."))
            if request.applicant_id == self.env.user and not self.env.is_superuser():
                raise UserError(_("El solicitante no puede aprobar su propia solicitud de pago."))
            if request.approver_id and request.approver_id != self.env.user and not self.env.is_superuser():
                raise UserError(
                    _("Solo el aprobador asignado (%s) puede aprobar esta solicitud.")
                    % request.approver_id.name
                )

            # Marcar actividad como terminada
            request.activity_feedback(["mail.mail_activity_data_todo"], feedback=_("Solicitud de pago aprobada."))

        self.write({
            "state": "approved",
            "approver_user_id": self.env.user.id,
            "approval_date": fields.Datetime.now(),
        })

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios con permisos de Aprobador pueden rechazar solicitudes de pago."))
        if self.state != "sent":
            raise UserError(_("Solo se pueden rechazar solicitudes en estado 'Enviada'."))
        if self.approver_id and self.approver_id != self.env.user and not self.env.is_superuser():
            raise UserError(
                _("Solo el aprobador asignado (%s) puede rechazar esta solicitud.")
                % self.approver_id.name
            )

        return {
            "name": _("Rechazar Solicitud de Pago"),
            "type": "ir.actions.act_window",
            "res_model": "payment.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_pay(self):
        self.ensure_one()
        if not self.env.user.has_group("payment_request.group_payment_request_treasury"):
            raise AccessError(_("Solo los usuarios de Tesorería pueden registrar pagos."))
        if self.state != "approved":
            raise UserError(_("Solo se pueden pagar solicitudes previamente aprobadas."))
        if self.payment_id:
            raise UserError(_("Esta solicitud ya cuenta con un pago contable registrado (%s).") % self.payment_id.name)

        return {
            "name": _("Registrar Pago"),
            "type": "ir.actions.act_window",
            "res_model": "payment.request.pay.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_view_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_("No hay ningún pago contable vinculado a esta solicitud."))
        return {
            "name": _("Pago Contable"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_reset_draft(self):
        for request in self:
            if request.state not in ("rejected", "draft"):
                raise UserError(_("Solo se pueden restablecer a borrador solicitudes rechazadas."))
        self.write({
            "state": "draft",
            "approver_id": False,
            "approver_user_id": False,
            "approval_date": False,
        })

    def unlink(self):
        if any(request.state != "draft" for request in self):
            raise UserError(_("Solo se pueden eliminar solicitudes en estado Borrador."))
        return super().unlink()
