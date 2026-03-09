from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    config_min_stock = fields.Float(
        string='Stock Mínimo',
        default=0.0,
        help='Umbral para generar alertas de stock crítico'
    )
    
    is_critical_stock = fields.Boolean(
        string='En Stock Crítico',
        default=False,
        help='Indica si el producto está actualmente por debajo del stock mínimo'
    )

