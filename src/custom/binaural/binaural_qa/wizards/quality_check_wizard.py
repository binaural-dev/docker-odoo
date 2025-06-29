from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class QualityCheckWizard(models.TransientModel):
    _name = 'quality.check.wizard'
    _description = 'Quality Check Wizard'

    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    status = fields.Selection([
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ], string='Result', required=True, default='approved')
    reason = fields.Text(string='Reason')

    @api.constrains('status', 'reason')
    def _check_reason_if_rejected(self):
        for record in self:
            if record.status == 'rejected' and not record.reason:
                raise ValidationError(_('Please provide a reason for rejection.'))

    def process_quality_check(self):
        self.ensure_one()
        picking = self.picking_id

        picking.write({
            'quality_check_state': self.status,
            'quality_check_reason': self.reason if self.status == 'rejected' else False,
            'quality_check_user_id': self.env.user.id,
            'quality_check_date': fields.Datetime.now(),
        })

        if self.status == 'approved':
            return picking.button_validate()
        else:
            return {'type': 'ir.actions.act_window_close'}