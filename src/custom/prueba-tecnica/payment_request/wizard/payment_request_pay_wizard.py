from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PaymentRequestPayWizard(models.TransientModel):
    _name = "payment.request.pay.wizard"
    _description = "Asistente de Registro de Pago de Solicitud"

    request_id = fields.Many2one("payment.request", string="Solicitud de Pago", required=True, readonly=True)
    company_id = fields.Many2one("res.company", related="request_id.company_id", readonly=True)
    partner_id = fields.Many2one("res.partner", related="request_id.partner_id", readonly=True)
    currency_id = fields.Many2one("res.currency", related="request_id.currency_id", readonly=True)
    amount = fields.Monetary(string="Monto", related="request_id.amount", readonly=True, currency_field="currency_id")
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de Pago",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        required=True,
        default=fields.Date.context_today,
    )
    communication = fields.Char(string="Memo / Referencia")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        request_id = res.get("request_id") or self.env.context.get("default_request_id")
        if request_id:
            req = self.env["payment.request"].browse(request_id)
            res["request_id"] = req.id
            res["communication"] = f"{req.name} - {req.concept}"
            default_journal = self.env["account.journal"].search([
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", req.company_id.id),
            ], limit=1)
            if default_journal:
                res["journal_id"] = default_journal.id
        return res

    def action_confirm_payment(self):
        self.ensure_one()
        req = self.request_id

        if not self.env.user.has_group("payment_request.group_payment_request_treasury"):
            raise AccessError(_("Solo los usuarios de Tesorería pueden registrar pagos."))
        if req.state != "approved":
            raise UserError(_("Solo se pueden pagar solicitudes en estado 'Aprobada'."))
        if req.payment_id:
            raise UserError(
                _("Esta solicitud ya cuenta con un pago contable registrado (%s). No se puede pagar dos veces.")
                % req.payment_id.name
            )

        payment_vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": req.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "date": self.payment_date,
            "journal_id": self.journal_id.id,
            "ref": self.communication or f"{req.name} - {req.concept}",
            "company_id": req.company_id.id,
        }

        # Seleccionar la línea de método de pago de salida del diario
        payment_method_line = self.journal_id.outbound_payment_method_line_ids[:1]
        if payment_method_line:
            payment_vals["payment_method_line_id"] = payment_method_line.id

        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()

        req.write({
            "state": "paid",
            "payment_id": payment.id,
        })

        req.message_post(
            body=_(
                "<b>Pago Registrado Exitosamente</b><br/>"
                "Se generó y confirmó el pago contable <b>%s</b> en el diario <b>%s</b>."
            )
            % (payment.name, self.journal_id.display_name),
            subtype_xmlid="mail.mt_comment",
        )

        return {
            "name": _("Pago Contable"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
            "target": "current",
        }

