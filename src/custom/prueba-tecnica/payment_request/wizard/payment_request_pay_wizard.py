from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PaymentRequestPayWizard(models.TransientModel):
    _name = "payment.request.pay.wizard"
    _description = "Asistente de Registro de Pago de Solicitud"

    request_id = fields.Many2one("payment.request", string="Solicitud de Pago", required=True, readonly=True)
    company_id = fields.Many2one("res.company", related="request_id.company_id", readonly=True)
    partner_id = fields.Many2one("res.partner", related="request_id.partner_id", readonly=True)
    currency_id = fields.Many2one("res.currency", related="request_id.currency_id", readonly=True)
    amount = fields.Monetary(string="Monto Solicitado", related="request_id.amount", readonly=True, currency_field="currency_id")
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de Pago",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    journal_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del Diario",
        compute="_compute_payment_values",
        store=True,
        readonly=True,
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        required=True,
        default=fields.Date.context_today,
    )
    exchange_rate = fields.Float(
        string="Tasa de Cambio",
        compute="_compute_payment_values",
        store=True,
        readonly=False,
        digits=(12, 4),
        help="Tasa oficial de cambio entre la moneda de la solicitud y la moneda del diario.",
    )
    payment_amount = fields.Monetary(
        string="Monto a Desembolsar",
        compute="_compute_payment_values",
        store=True,
        readonly=False,
        currency_field="journal_currency_id",
        help="Monto efectivo a desembolsar en la moneda del diario seleccionado a la tasa de pago.",
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

    @api.depends("journal_id", "payment_date", "request_id")
    def _compute_payment_values(self):
        for wizard in self:
            if not wizard.request_id or not wizard.journal_id:
                base_currency = wizard.company_id.currency_id or wizard.env.company.currency_id
                wizard.journal_currency_id = base_currency
                wizard.exchange_rate = 1.0
                wizard.payment_amount = wizard.amount or 0.0
                continue

            target_currency = wizard.journal_id.currency_id or wizard.journal_id.company_id.currency_id
            wizard.journal_currency_id = target_currency
            date = wizard.payment_date or fields.Date.context_today(wizard)

            if wizard.currency_id == target_currency:
                wizard.exchange_rate = 1.0
                wizard.payment_amount = wizard.amount
            else:
                # Conversión oficial de Odoo según res.currency.rate a la fecha de pago
                converted_amount = wizard.currency_id._convert(
                    wizard.amount, target_currency, wizard.company_id, date
                )
                wizard.payment_amount = converted_amount
                wizard.exchange_rate = (
                    converted_amount / wizard.amount if wizard.amount else 1.0
                )

    @api.onchange("exchange_rate")
    def _onchange_exchange_rate(self):
        if self.currency_id != self.journal_currency_id and self.exchange_rate > 0:
            self.payment_amount = self.journal_currency_id.round(self.amount * self.exchange_rate)

    @api.onchange("payment_amount")
    def _onchange_payment_amount(self):
        if self.currency_id != self.journal_currency_id and self.amount > 0:
            self.exchange_rate = self.payment_amount / self.amount

    def action_confirm_payment(self):
        self.ensure_one()
        req = self.request_id

        # 1. Verificación de permisos de usuario
        if not self.env.user.has_group("payment_request.group_payment_request_treasury"):
            raise AccessError(_("Solo los usuarios de Tesorería pueden registrar pagos."))

        # 2. Bloqueo a nivel de base de datos para prevenir condiciones de carrera (FOR UPDATE NOWAIT)
        try:
            self.env.cr.execute(
                "SELECT id, state FROM payment_request WHERE id = %s FOR UPDATE NOWAIT",
                [req.id],
            )
        except Exception:
            raise UserError(
                _("La solicitud está siendo procesada concurrentemente por otro usuario. Por favor, reintente en unos momentos.")
            )

        # 3. Re-validación del estado y unicidad bajo el bloqueo exclusivo en BD
        req.invalidate_recordset(["state", "payment_id"])
        if req.state != "approved":
            raise UserError(_("Solo se pueden pagar solicitudes en estado 'Aprobada'."))
        if req.payment_id:
            raise UserError(
                _("Esta solicitud ya cuenta con un pago contable registrado (%s). No se puede pagar dos veces.")
                % req.payment_id.name
            )

        # 4. Creación del asiento contable de pago a proveedor (account.payment)
        target_currency = self.journal_currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id
        amount_to_pay = self.payment_amount if self.currency_id != target_currency else self.amount

        payment_vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": req.partner_id.id,
            "amount": amount_to_pay,
            "currency_id": target_currency.id,
            "date": self.payment_date,
            "journal_id": self.journal_id.id,
            "ref": self.communication or f"{req.name} - {req.concept}",
            "company_id": req.company_id.id,
        }

        payment_method_line = self.journal_id.outbound_payment_method_line_ids[:1]
        if payment_method_line:
            payment_vals["payment_method_line_id"] = payment_method_line.id

        # Si create() o action_post() fallan, se levanta la excepción y la solicitud NUNCA pasa a 'paid'
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()

        # 5. Transición de estado de la solicitud únicamente tras el éxito del pago contable
        req.write({
            "state": "paid",
            "payment_id": payment.id,
        })

        if req.currency_id != target_currency:
            detail_msg = _(
                "<b>Pago Registrado Exitosamente (Multimoneda)</b><br/>"
                "Se generó y confirmó el pago contable <b>%s</b> en el diario <b>%s</b>.<br/>"
                "<b>Monto Original Solicitado:</b> %s %s<br/>"
                "<b>Monto Pagado en Diario:</b> %s %s (Tasa: %s)"
            ) % (
                payment.name,
                self.journal_id.display_name,
                req.amount,
                req.currency_id.symbol or req.currency_id.name,
                amount_to_pay,
                target_currency.symbol or target_currency.name,
                f"{self.exchange_rate:.4f}" if self.exchange_rate else "N/A",
            )
        else:
            detail_msg = _(
                "<b>Pago Registrado Exitosamente</b><br/>"
                "Se generó y confirmó el pago contable <b>%s</b> en el diario <b>%s</b>."
            ) % (payment.name, self.journal_id.display_name)

        req.message_post(body=detail_msg, subtype_xmlid="mail.mt_comment")

        return {
            "name": _("Pago Contable"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
            "target": "current",
        }
