from odoo import fields, models


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

    def action_confirm(self):
        self.ensure_one()
        payment = self.request_id._create_payment(self.journal_id, self.payment_date)
        return {"type": "ir.actions.act_window_close", "infos": {"payment_id": payment.id}}
