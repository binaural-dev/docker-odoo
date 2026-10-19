from odoo import models, fields


class ShopApiLog(models.Model):
    _name = 'shop.api.log'
    _description = 'Registro de Auditoría de Llamadas API'
    _order = 'create_date desc'

    endpoint = fields.Char(string='Endpoint', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Usuario', ondelete='set null')
    response_code = fields.Integer(string='Código de Respuesta HTTP', required=True)
    duration = fields.Float(string='Duración (s)', digits=(6, 4))