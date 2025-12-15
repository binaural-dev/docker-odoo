from odoo import _, fields, models, api
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):

    _inherit = 'product.template'

    minimum_stock = fields.Float()
    low_stock = fields.Boolean(default=False)

    

    @api.constrains('minimum_stock')
    def check_for_critical_qty(self):
        if self.qty_available < self.minimum_stock:
            self.low_stock = True
            self.stock_warning()
        else:
            self.low_stock = False

    def stock_warning(self):
        target_group = self.env.ref('critic_stock_warning.purchase_stock_group')
        users_in_group = self.env['res.users'].search([('groups_id', 'in', target_group.id)])
      # Enviamos el mensaje de notificacion
        for user in users_in_group:

            self.send_odoo_bot_message(
                user_id=user.id,
                message_body=self._get_message_notification(user)
            )

    # Metodo para enviar el mensaje de notificacion interna

    def send_odoo_bot_message(self, user_id, message_body):
        # 1. Obtener el usuario root (administrador) y el usuario destino
        root_partner = self.env.user.sudo().id
        target_user = self.env['res.users'].browse(user_id)
        target_partner = target_user.partner_id

        # 2. Buscar un canal CHAT existente entre root y el usuario destino (exactamente 2 miembros)
        domain = [
            ('channel_type', '=', 'chat'),
            ('channel_partner_ids', 'in', [root_partner]),
            ('channel_partner_ids', 'in', [target_partner.id]),
        ]
        channel = self.env['discuss.channel'].sudo().search(domain, limit=1)

        # 3. Crear el canal si no existe
        if not channel:
            channel = self.env['discuss.channel'].sudo().create({
                'name': f'Chat  {target_partner.name}',
                'channel_type': 'chat',
                'channel_member_ids': [
                    (0, 0, {'partner_id': target_partner.id}),
                ],
            })
        
        # 4. Enviar mensaje como el usuario root
        channel.sudo().message_post(
            body=message_body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id= root_partner,  # Siempre usa el root como autor
        )

    def _get_message_notification(self, user):
        return self.env["ir.qweb"]._render(
            "critic_stock_warning.stock_notification",
            {
                'user':user,
                'product_id': self
            }
        )
    
    # def action_view_critical_stock_products(self):
    #     action = self.env['ir.actions.actions']._for_xml_id('product.product_template_kanban_view')
    #     _logger.info("##########################")
    #     _logger.info(action.read())
    #     action['domain'] = [('qty_available', '<', 'minimum_stock')]
    #     return action
