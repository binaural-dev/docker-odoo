from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PaymentRequest(models.Model):
    """Modelo para formalizar solicitudes de pago a proveedores con flujo de aprobación."""

    _name = "payment.request"
    _description = "Solicitud de Pago"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Secuencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
        help="Número correlativo autogenerado (ej. SP/2026/0001).",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        required=True,
        tracking=True,
        help="Proveedor al que se le realizará el pago.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="Empleado o usuario que genera la solicitud.",
    )
    amount = fields.Monetary(
        string="Monto",
        required=True,
        currency_field="currency_id",
        tracking=True,
        help="Monto a pagar, debe ser estrictamente mayor a 0.",
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
        string="Fecha de Solicitud",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    concept = fields.Text(
        string="Concepto del Pago",
        required=True,
        tracking=True,
        help="Motivo o justificación de la solicitud de pago.",
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("submitted", "Enviada"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # RESTRICCIONES DE INTEGRIDAD Y REGLAS DE NEGOCIO
    # -------------------------------------------------------------------------
    @api.constrains("amount")
    def _check_amount(self):
        """Valida que el monto solicitado no sea cero ni negativo."""
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("El monto de la solicitud debe ser estrictamente mayor a cero."))

    def write(self, vals):
        """Impide modificar los datos sustantivos de la solicitud una vez enviada."""
        protected_fields = {"partner_id", "amount", "currency_id", "date", "concept"}
        for record in self:
            if record.state != "draft" and any(field in vals for field in protected_fields):
                raise UserError(_("No puede modificar una solicitud que ya ha sido enviada o procesada."))
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Asigna la secuencia oficial correlativa al crear la solicitud."""
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code("payment.request") or _("Nuevo")
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # ACCIONES DEL FLUJO DE APROBACIÓN
    # -------------------------------------------------------------------------
    def action_submit(self):
        """Pasa la solicitud de Borrador a Enviada."""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Solo se pueden enviar solicitudes en estado Borrador."))
            record.state = "submitted"
            record.message_post(body=_("Solicitud de pago enviada para aprobación."))
        return True

    def action_approve(self):
        """Aprueba la solicitud. Restringido a usuarios con el grupo Aprobador."""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado Enviada."))
            # Verificación de seguridad a nivel de método (Backend validation)
            if not self.env.user.has_group("payment_request.group_payment_request_approver") and not self.env.is_admin():
                raise AccessError(_("No tiene permisos para aprobar solicitudes de pago."))
            record.state = "approved"
            record.message_post(body=_("Solicitud aprobada por %s.") % self.env.user.name)
        return True

    def action_reject(self):
        """Rechaza la solicitud. Restringido a usuarios con el grupo Aprobador."""
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("No se puede rechazar una solicitud en estado %s.") % record.state)
            if not self.env.user.has_group("payment_request.group_payment_request_approver") and not self.env.is_admin():
                raise AccessError(_("No tiene permisos para rechazar solicitudes de pago."))
            record.state = "rejected"
            record.message_post(body=_("Solicitud rechazada por %s.") % self.env.user.name)
        return True

    def action_pay(self):
        """Registra el pago de la solicitud. Restringido al grupo Tesorería."""
        for record in self:
            if record.state != "approved":
                raise UserError(_("Solo se pueden pagar solicitudes previamente Aprobadas."))
            if not self.env.user.has_group("payment_request.group_payment_request_treasury") and not self.env.is_admin():
                raise AccessError(_("Solo el personal de Tesorería puede registrar el pago de solicitudes."))
            record.state = "paid"
            record.message_post(body=_("Solicitud marcada como pagada por %s.") % self.env.user.name)
        return True

    def action_draft(self):
        """Permite restablecer a borrador desde rechazada."""
        for record in self:
            if record.state != "rejected":
                raise UserError(_("Solo se pueden reiniciar a borrador solicitudes rechazadas."))
            record.state = "draft"
            record.message_post(body=_("Solicitud restablecida a borrador."))
        return True
