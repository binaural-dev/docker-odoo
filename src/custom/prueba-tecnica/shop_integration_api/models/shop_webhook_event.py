import hashlib
import hmac
import json
import logging
import threading
from datetime import timedelta

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

PARAM_URL = "shop_integration_api.webhook_url"
PARAM_SECRET = "shop_integration_api.webhook_secret"
TIMEOUT_SECONDS = 10
# Espera antes de cada reintento (minutos). Tras el último, el evento queda «fallido» (~8 h en total).
RETRY_DELAYS_MINUTES = [1, 5, 15, 30, 60, 120, 240]
MAX_ATTEMPTS = len(RETRY_DELAYS_MINUTES) + 1


class ShopWebhookEvent(models.Model):
    """Cola de avisos salientes a la tienda. Se envían fuera de la transacción de quien valida la entrega."""

    _name = "shop.webhook.event"
    _description = "Aviso (webhook) a la tienda en línea"
    _order = "id desc"
    _rec_name = "event_type"

    event_type = fields.Char(string="Evento", required=True, readonly=True)
    order_id = fields.Many2one("sale.order", string="Pedido", readonly=True, ondelete="set null")
    picking_id = fields.Many2one("stock.picking", string="Entrega", readonly=True, ondelete="set null")
    payload = fields.Text(string="Contenido (JSON)", required=True, readonly=True)
    state = fields.Selection(
        [("pending", "Pendiente"), ("sent", "Enviado"), ("failed", "Fallido")],
        string="Estado", required=True, default="pending", readonly=True, index=True,
    )
    attempts = fields.Integer(string="Intentos", readonly=True)
    next_attempt_at = fields.Datetime(string="Próximo intento", default=fields.Datetime.now, readonly=True, index=True)
    sent_at = fields.Datetime(string="Enviado el", readonly=True)
    last_status_code = fields.Integer(string="Último código HTTP", readonly=True)
    last_error = fields.Char(string="Último error", readonly=True)

    # Encolar

    @api.model
    def _enqueue_deliveries(self, pickings):
        """Crea un evento «order.delivered» por entrega validada y pide a la acción planificada que lo envíe."""
        if not self.env["ir.config_parameter"].sudo().get_param(PARAM_URL):
            _logger.info("shop_integration_api: sin %s configurado; no se encolan avisos", PARAM_URL)
            return self.browse()
        events = self.create([
            {
                "event_type": "order.delivered",
                "order_id": picking.sale_id.id,
                "picking_id": picking.id,
                "payload": "{}",  # se completa abajo, cuando el evento ya tiene id
            }
            for picking in pickings
        ])
        for event in events:
            event.payload = json.dumps(event._build_delivery_payload(), ensure_ascii=False)
        self.env.ref("shop_integration_api.ir_cron_shop_webhook_send")._trigger()
        return events

    def _build_delivery_payload(self):
        self.ensure_one()
        picking, order = self.picking_id, self.order_id
        return {
            "event": "order.delivered",
            "event_id": self.id,
            "occurred_at": picking.date_done.replace(microsecond=0).isoformat() + "Z",
            "order": {"id": order.id, "name": order.name, "external_ref": order.shop_external_ref},
            "delivery": {
                "id": picking.id,
                "name": picking.name,
                "is_partial": bool(picking.backorder_ids),
                "is_backorder": bool(picking.backorder_id),
            },
            "lines": [
                {"default_code": move.product_id.default_code, "quantity": move.quantity}
                for move in picking.move_ids.filtered(lambda m: m.state == "done")
            ],
        }

    # Enviar

    @api.model
    def _cron_send_pending(self, limit=50):
        """Envía los avisos pendientes cuyo próximo intento ya llegó. Un aviso que falla se reprograma."""
        params = self.env["ir.config_parameter"].sudo()
        url, secret = params.get_param(PARAM_URL), params.get_param(PARAM_SECRET) or ""
        if not url:
            return
        due = self.search(
            [("state", "=", "pending"), ("next_attempt_at", "<=", fields.Datetime.now())],
            order="next_attempt_at, id", limit=limit,
        )
        auto_commit = not getattr(threading.current_thread(), "testing", False)
        for event in due:
            # Si otra ejecución ya lo tomó, se salta (no se envía dos veces a la vez).
            self.env.cr.execute(
                "SELECT id FROM shop_webhook_event WHERE id = %s AND state = 'pending' FOR UPDATE SKIP LOCKED",
                [event.id],
            )
            if not self.env.cr.fetchone():
                continue
            event._send(url, secret)
            if auto_commit:
                self.env.cr.commit()  # cada aviso queda registrado aunque falle el siguiente

    def _send(self, url, secret):
        self.ensure_one()
        body = self.payload.encode()
        headers = {
            "Content-Type": "application/json",
            "X-Shop-Event": self.event_type,
            # La tienda debe ignorar un event_id que ya procesó: un reintento puede llegar dos veces.
            "X-Shop-Event-Id": str(self.id),
            "X-Shop-Signature": "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
        }
        status, error = 0, False
        try:
            response = requests.post(url, data=body, headers=headers, timeout=TIMEOUT_SECONDS)
            status = response.status_code
            if not 200 <= status < 300:
                error = _("La tienda respondió HTTP %s", status)
        except requests.RequestException as exc:
            error = _("No se pudo conectar con la tienda: %s", exc.__class__.__name__)
        attempts = self.attempts + 1
        vals = {"attempts": attempts, "last_status_code": status, "last_error": error}
        if not error:
            vals.update(state="sent", sent_at=fields.Datetime.now())
        elif attempts >= MAX_ATTEMPTS:
            vals["state"] = "failed"
            _logger.warning("shop_integration_api: aviso %s fallido tras %s intentos: %s", self.id, attempts, error)
        else:
            vals["next_attempt_at"] = fields.Datetime.now() + timedelta(minutes=RETRY_DELAYS_MINUTES[attempts - 1])
        self.write(vals)
        return not error

    def action_retry_now(self):
        """Botón para administradores: vuelve a intentar ya un aviso pendiente o fallido."""
        self.filtered(lambda e: e.state != "sent").write(
            {"state": "pending", "next_attempt_at": fields.Datetime.now()}
        )
        self.env.ref("shop_integration_api.ir_cron_shop_webhook_send")._trigger()
