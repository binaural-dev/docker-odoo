from odoo import models, fields


class ShopIdempotencyKey(models.Model):
    _name = 'shop.idempotency.key'
    _description = 'Claves de Idempotencia'

    key = fields.Char(string='Clave', required=True, index=True)
    request_hash = fields.Char(string='Hash del Payload', required=True)
    response_code = fields.Integer(string='Código de Respuesta')
    response_body = fields.Text(string='Cuerpo de la Respuesta')
    order_id = fields.Many2one('sale.order', string='Pedido Creado', ondelete='cascade')