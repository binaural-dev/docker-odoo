from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quality_check_state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Quality Check State', default='pending', copy=False,)

    quality_check_required = fields.Boolean(
        string='Require Quality Check',
        related='company_id.quality_check_required',
        readonly=True,
        store=False
    )

    quality_check_reason = fields.Text(
        string='Quality Check Reason',
        copy=False,
    )

    quality_check_user_id = fields.Many2one(
        'res.users',
        string='Quality Check User',
        copy=False,
    )

    quality_check_date = fields.Datetime(
        string='Date of Quality Check',
        copy=False,
    )

    def button_validate(self):
        for picking in self:
            if picking.state == 'assigned' and picking.quality_check_required and picking.quality_check_state == 'pending':
                return {
                    'name': _('Quality Check'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'quality.check.wizard',
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'context': {'default_picking_id': picking.id},
                    'target': 'new',
                }
            elif picking.quality_check_state == 'rejected':
                raise UserError(
                    _("Rejected Transfer: %s") % (
                                picking.quality_check_reason or 'No reason provided'))

        return super(StockPicking, self).button_validate()