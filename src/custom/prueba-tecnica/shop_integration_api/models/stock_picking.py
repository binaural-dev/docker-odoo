import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        shop_deliveries = self.filtered(
            lambda p: p.state == "done" and p.picking_type_code == "outgoing" and p.sale_id.shop_external_ref
        )
        if shop_deliveries:
            try:
                # Savepoint: si encolar el aviso fallara, la validación de la entrega sigue igual.
                with self.env.cr.savepoint():
                    # sudo(): quien valida (almacén) no tiene ni necesita acceso a la cola de avisos.
                    self.env["shop.webhook.event"].sudo()._enqueue_deliveries(shop_deliveries)
            except Exception:
                _logger.exception("shop_integration_api: no se pudo encolar el aviso de %s", shop_deliveries.ids)
        return res
