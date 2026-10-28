from odoo import fields, models


class PaymentRequestRejectWizard(models.TransientModel):
    _name = "payment.request.reject.wizard"
    _description = "Rechazar solicitud de pago"

    request_id = fields.Many2one("payment.request", string="Solicitud", required=True, readonly=True)
    reason = fields.Text(string="Motivo", required=True, help="El solicitante lo verá en el historial de la solicitud.")

    def action_confirm(self):
        self.ensure_one()
        self.request_id.action_reject(self.reason)
        return {"type": "ir.actions.act_window_close"}
