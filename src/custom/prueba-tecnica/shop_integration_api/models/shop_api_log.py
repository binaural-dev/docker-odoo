from odoo import api, fields, models


class ShopApiLog(models.Model):
    _name = "shop.api.log"
    _description = "Registro de llamadas a la API de la tienda"
    _order = "id desc"
    _rec_name = "endpoint"

    endpoint = fields.Char(string="Endpoint", required=True, readonly=True)
    method = fields.Char(string="Método", required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Usuario", readonly=True, ondelete="set null",
        help="Vacío cuando la llamada no se pudo autenticar.",
    )
    status_code = fields.Integer(string="Código HTTP", required=True, readonly=True)
    error_code = fields.Char(string="Código de error", readonly=True)
    duration_ms = fields.Float(string="Duración (ms)", digits=(16, 1), readonly=True)
    remote_addr = fields.Char(string="IP de origen", readonly=True)
    external_ref = fields.Char(string="Referencia externa", readonly=True)
    order_id = fields.Many2one("sale.order", string="Pedido creado", readonly=True, ondelete="set null")
    success = fields.Boolean(string="Correcta", compute="_compute_success", store=True)

    @api.depends("status_code")
    def _compute_success(self):
        for log in self:
            log.success = 200 <= log.status_code < 300
