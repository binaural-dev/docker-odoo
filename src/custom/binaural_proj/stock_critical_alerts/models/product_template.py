from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_minimum = fields.Float(
        string='Minimum Stock',
        default=0.0,
        help='Minimum stock level. An alert will be generated when available quantity falls below this value.'
    )
    stock_alert_sent = fields.Boolean(
        string='Alert Sent',
        default=False,
        copy=False,
    )

    def _check_stock_critical(self):
        products = self.search([
            ('stock_minimum', '>', 0),
            ('type', '=', 'product'),
        ])
        for product in products:
            product.invalidate_recordset(['qty_available'])
            if product.qty_available < product.stock_minimum:
                if not product.stock_alert_sent:
                    _logger.info('Sending stock alert for product %s', product.name)
                    product._send_stock_alert()
                    product.stock_alert_sent = True
            else:
                if product.stock_alert_sent:
                    product.stock_alert_sent = False

    def _send_stock_alert(self):
        self.ensure_one()

        body_format ="""Critical Stock Alert: Product "%s" has fallen below minimum stock level. '
                 'Current stock: %s, Minimum required: %s'""" % (
                     self.name,
                     self.qty_available,
                     self.stock_minimum,
                 )
        
        subject_format ="""Critical Stock Alert: %s""" % self.name
        
        self.message_post(
            body=body_format,
            subject=subject_format,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if not stock_manager_group:
            return

        manager_users = stock_manager_group.users
        if not manager_users:
            return

        partner_ids = manager_users.mapped('partner_id').ids
        self.message_notify(
            partner_ids=partner_ids,
            body=body_format,
            subject=subject_format,
        )

        

    @api.model
    def _cron_check_stock_critical(self):
        self._check_stock_critical()
