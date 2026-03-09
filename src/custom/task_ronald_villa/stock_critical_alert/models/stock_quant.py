from odoo import models, api, _

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity=0.0, lot_id=None, package_id=None, owner_id=None, in_date=None, **kwargs):
        """
        Sobrescribe el método nativo que actualiza las cantidades disponibles (stock) en Odoo.
        Es invocado cada vez que se efectúa un movimiento de inventario, transferencia, ajuste, etc.
        """
        res = super()._update_available_quantity(
            product_id, location_id, quantity=quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id, in_date=in_date, **kwargs
        )
        
        if location_id.usage == 'internal':
            product_id.invalidate_recordset(['qty_available'])
            qty_after = product_id.qty_available
            min_stock = product_id.config_min_stock
            
            is_critical = qty_after < min_stock
            
            template = product_id.product_tmpl_id
            
            if is_critical and not template.is_critical_stock:
                template.is_critical_stock = True
                template.message_post(
                    body=_("Alerta de Stock Crítico: El nivel de inventario ha caído a %s (por debajo del umbral de %s).") % (qty_after, min_stock),
                    subject=_("Alerta de Stock Crítico"),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
            elif not is_critical and template.is_critical_stock:
                template.is_critical_stock = False

        return res
