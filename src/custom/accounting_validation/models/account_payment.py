from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    finance_validation = fields.Boolean(
        string='Validado por Finanzas',
        default=False,
        copy=False
    )

    def action_post(self):
        for payment in self:
            if payment._requires_double_validation() and not payment.finance_validation:
                raise UserError(_(f'Este pago requiere validación adicional por el departamento de finanzas por exceder el límite configurado de ${payment.company_id.payment_validation_limit:.2f}'))
        return super().action_post()

    @api.model
    def create(self, vals):
        payment = super(AccountPayment, self).create(vals)
        payment._check_validation_required()
        return payment

    def write(self, vals):
        result = super(AccountPayment, self).write(vals)
        if 'amount' in vals or 'state' in vals:
            self._check_validation_required()
        return result

    def _check_validation_required(self):
        for payment in self:
            if payment.state == 'posted' and payment._requires_double_validation():
                if not payment.finance_validation:
                    raise UserError(_(f'Este pago requiere validación adicional por el departamento de finanzas por exceder el límite configurado de ${payment.company_id.payment_validation_limit:.2f}'))

    def _requires_double_validation(self):
        self.ensure_one()
        return (
            self.company_id.payment_validation_limit > 0 and
            self.amount >= self.company_id.payment_validation_limit
        )

    def action_validate_finance(self):
        """Acción para marcar como validado por finanzas"""
        self.ensure_one()
        if not self.finance_validation:
            self.write({'finance_validation': True})
        return True