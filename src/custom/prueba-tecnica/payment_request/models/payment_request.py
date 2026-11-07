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
        self.write({"state": "sent"})

    def action_approve(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios con permisos de Aprobador pueden aprobar solicitudes de pago."))
        for request in self:
            if request.applicant_id == self.env.user and not self.env.is_superuser():
                raise UserError(_("El solicitante no puede aprobar su propia solicitud de pago."))
            if request.state != "sent":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado 'Enviada'."))
        self.write({"state": "approved"})

    def action_reject(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios con permisos de Aprobador pueden rechazar solicitudes de pago."))
        for request in self:
            if request.state != "sent":
                raise UserError(_("Solo se pueden rechazar solicitudes en estado 'Enviada'."))
        self.write({"state": "rejected"})

    def action_pay(self):
        if not self.env.user.has_group("payment_request.group_payment_request_treasury"):
            raise AccessError(_("Solo los usuarios de Tesorería pueden registrar pagos."))
        for request in self:
            if request.state != "approved":
                raise UserError(_("Solo se pueden pagar solicitudes previamente aprobadas."))
        self.write({"state": "paid"})

    def action_reset_draft(self):
        for request in self:
            if request.state not in ("rejected", "draft"):
                raise UserError(_("Solo se pueden restablecer a borrador solicitudes rechazadas."))
        self.write({"state": "draft"})

    def unlink(self):
        if any(request.state != "draft" for request in self):
            raise UserError(_("Solo se pueden eliminar solicitudes en estado Borrador."))
        return super().unlink()

