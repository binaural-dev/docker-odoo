from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _onchange_partner_apply_discount(self):
        if self.move_type in ('out_invoice', 'out_refund') and self.partner_id:
            self._apply_customer_discount()

    def action_post(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and move.partner_id:
                move._apply_customer_discount()
        return super().action_post()

    def _get_discount_rule(self):
        self.ensure_one()
        if not self.partner_id or not self.partner_id.customer_type_id:
            return self.env['account.discount.rule']

        rule = self.env['account.discount.rule'].search([
            ('customer_type_id', '=', self.partner_id.customer_type_id.id),
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        return rule

    def _apply_customer_discount(self):
        self.ensure_one()
        discount_rule = self._get_discount_rule()
        lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product' or (not l.display_type and l.product_id))

        if not discount_rule:
            for line in lines:
                line.discount = 0.0
            return

        amount_total = sum(line.price_unit * line.quantity for line in lines)

        if discount_rule.min_amount > 0 and amount_total < discount_rule.min_amount:
            for line in lines:
                line.discount = 0.0
            return
        for line in lines:
            line.discount = discount_rule.discount_percentage


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id', 'quantity', 'price_unit')
    def _onchange_product_apply_discount(self):
        if self.move_id.move_type in ('out_invoice', 'out_refund') and self.move_id.partner_id:
            self.move_id._apply_customer_discount()
