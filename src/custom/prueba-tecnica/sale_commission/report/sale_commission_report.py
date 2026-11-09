from odoo import fields, models, tools


class SaleCommissionReport(models.Model):
    _name = "sale.commission.report"
    _description = "Análisis de comisiones"
    _auto = False
    _order = "date desc"

    date = fields.Date(string="Fecha", readonly=True)
    user_id = fields.Many2one("res.users", string="Vendedor", readonly=True)
    order_id = fields.Many2one("sale.order", string="Pedido", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    amount_untaxed = fields.Monetary(string="Vendido sin impuestos", readonly=True)
    commission_amount = fields.Monetary(string="Comisión", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    l.id AS id,
                    o.date_order::date AS date,
                    o.user_id AS user_id,
                    o.id AS order_id,
                    o.partner_id AS partner_id,
                    l.product_id AS product_id,
                    o.company_id AS company_id,
                    l.currency_id AS currency_id,
                    l.price_subtotal AS amount_untaxed,
                    l.commission_amount AS commission_amount
                FROM sale_order_line l
                JOIN sale_order o ON o.id = l.order_id
                WHERE o.state = 'sale'
                  AND l.display_type IS NULL
            )
            """
        )
