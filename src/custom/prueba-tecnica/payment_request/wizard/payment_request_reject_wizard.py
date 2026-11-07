from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class PaymentRequestRejectWizard(models.TransientModel):
    _name = "payment.request.reject.wizard"
    _description = "Asistente de Rechazo de Solicitud de Pago"

    request_id = fields.Many2one("payment.request", string="Solicitud de Pago", required=True, readonly=True)
    reason = fields.Text(string="Motivo de Rechazo", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        req = self.request_id
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios con permisos de Aprobador pueden rechazar solicitudes de pago."))
        if req.state != "sent":
            raise UserError(_("Solo se pueden rechazar solicitudes en estado 'Enviada'."))
        if req.approver_id and req.approver_id != self.env.user and not self.env.is_superuser():
            raise UserError(
                _("Solo el aprobador asignado (%s) puede rechazar esta solicitud.")
                % req.approver_id.name
            )
        if not self.reason or not self.reason.strip():
            raise UserError(_("El motivo de rechazo es obligatorio."))

        # Publicar motivo en el chatter
        clean_reason = self.reason.strip()
        req.message_post(
            body=_("<b>Solicitud Rechazada</b><br/><b>Motivo:</b> %s") % clean_reason,
            subtype_xmlid="mail.mt_comment",
        )

        # Cerrar actividad pendiente
        req.activity_feedback(["mail.mail_activity_data_todo"], feedback=_("Rechazada: %s") % clean_reason)

        req.write({
            "state": "rejected",
            "reject_reason": clean_reason,
        })
        return {"type": "ir.actions.act_window_close"}

