import hashlib
import json

from odoo import api, fields, models


class ShopApiIdempotency(models.Model):
    """Claves Idempotency-Key ya usadas en POST /api/v1/orders, por usuario de la integración."""

    _name = "shop.api.idempotency"
    _description = "Clave de idempotencia de la API de la tienda"
    _order = "id desc"

    key = fields.Char(required=True, readonly=True, index=True)
    user_id = fields.Many2one("res.users", required=True, readonly=True, ondelete="cascade")
    request_hash = fields.Char(
        string="Huella del contenido", required=True, readonly=True,
        help="SHA-256 del cuerpo JSON normalizado (claves ordenadas): distingue un reintento de un pedido distinto.",
    )
    order_id = fields.Many2one("sale.order", string="Pedido", readonly=True, ondelete="set null")

    _sql_constraints = [
        ("key_user_uniq", "unique(key, user_id)", "Esa Idempotency-Key ya se usó."),
    ]

    @api.model
    def _hash_payload(self, payload):
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()
