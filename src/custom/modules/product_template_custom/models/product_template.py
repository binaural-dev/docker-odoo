from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    minimum_stock_alert = fields.Float(string='Stock Mínimo (Alerta)', default=0.0)
    is_stock_critical = fields.Boolean(
        string='Stock Crítico',
        compute='_compute_is_stock_critical',
        search='_search_is_stock_critical',
        store=True
    )
    alert_sent = fields.Boolean(string='Alerta Enviada', default=False, copy=False)

    def write(self, vals):
        # Si cambian el umbral mínimo, resetear la alerta para que el cron la re-evalúe
        if 'minimum_stock_alert' in vals:
            vals['alert_sent'] = False
        return super().write(vals)

    @api.depends('qty_available', 'minimum_stock_alert')
    def _compute_is_stock_critical(self):
        for product in self:
            product.is_stock_critical = product.qty_available < product.minimum_stock_alert

    def _search_is_stock_critical(self, operator, value):
        """Permite buscar por is_stock_critical en dominios (dashboard, filtros, etc.)."""
        products = self.search([('minimum_stock_alert', '>', 0)])
        critical_ids = [p.id for p in products if p.qty_available < p.minimum_stock_alert]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', critical_ids)]
        return [('id', 'not in', critical_ids)]

    @api.model
    def _cron_check_critical_stock(self):
        """Acción automática evaluada por el Cron"""
        # Forzar recomputación: qty_available no es almacenado y no dispara
        # la recomputación automática de is_stock_critical
        all_with_alert = self.search([('minimum_stock_alert', '>', 0)])
        all_with_alert._compute_is_stock_critical()

        # 1. Buscar productos en estado crítico que no tengan alerta enviada
        critical_products = self.search([
            ('is_stock_critical', '=', True),
            ('alert_sent', '=', False)
        ])
        
        for prod in critical_products:
            msg = f"⚠️ ALERTA: El stock del producto ha caído a {prod.qty_available}, por debajo del umbral mínimo configurado ({prod.minimum_stock_alert})."
            
            # Esto genera automáticamente un registro en el modelo 'mail.message'
            # y lo adjunta al historial del producto (Chatter).

            ## MEJORA PROPUESTA: Consultar correctamente solamente los usuarios que tengan permiso de administracion en inventario 
            admin_partner = self.env.ref('base.partner_admin')
            
            prod.message_post(
                body=msg, 
                message_type='notification', # Mejor estándar para alertas automáticas
                subtype_xmlid='mail.mt_note', # Nota interna
                partner_ids=[admin_partner.id] # ¡Esto activa la burbujita!
            )
            prod.alert_sent = True

        # 2. Resetear alerta si el stock se recuperó mediante un ingreso de mercancía
        recovered_products = self.search([
            ('is_stock_critical', '=', False),
            ('alert_sent', '=', True)
        ])
        if recovered_products:
            recovered_products.write({'alert_sent': False})