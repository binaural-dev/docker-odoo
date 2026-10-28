from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentRequestPaymentWizard(models.TransientModel):
    _name = "payment.request.payment.wizard"
    _description = "Registrar pago de una solicitud"

    request_id = fields.Many2one("payment.request", string="Solicitud", required=True, readonly=True)
    company_id = fields.Many2one(related="request_id.company_id")
    partner_id = fields.Many2one(related="request_id.partner_id", string="Proveedor")
    amount = fields.Monetary(related="request_id.amount", string="Monto", currency_field="currency_id")
    currency_id = fields.Many2one(related="request_id.currency_id")
    journal_id = fields.Many2one(
        "account.journal", string="Diario", required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_date = fields.Date(string="Fecha del pago", required=True, default=fields.Date.context_today)
    # Vista previa de lo que se va a pagar (misma lógica que el pago real).
    payment_currency_id = fields.Many2one("res.currency", string="Moneda del pago", compute="_compute_preview")
    payment_amount = fields.Monetary(
        string="Monto a pagar", currency_field="payment_currency_id", compute="_compute_preview",
    )
    payment_rate = fields.Float(string="Tasa", digits=(16, 6), compute="_compute_preview")
    preview_warning = fields.Char(compute="_compute_preview")

    @api.depends("journal_id", "payment_date", "request_id")
    def _compute_preview(self):
        for wizard in self:
            wizard.preview_warning = False
            wizard.payment_currency_id = wizard.journal_id.currency_id or wizard.company_id.currency_id
            wizard.payment_amount = wizard.payment_rate = 0.0
            if not (wizard.journal_id and wizard.payment_date and wizard.request_id):
                continue
            try:
                currency, amount, rate = wizard.request_id._get_payment_conversion(
                    wizard.journal_id, wizard.payment_date
                )
            except UserError as error:
                wizard.preview_warning = error.args[0]
                continue
            wizard.payment_currency_id, wizard.payment_amount, wizard.payment_rate = currency, amount, rate

    def action_confirm(self):
        self.ensure_one()
        payment = self.request_id._create_payment(self.journal_id, self.payment_date)
        return {"type": "ir.actions.act_window_close", "infos": {"payment_id": payment.id}}
