from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shop_external_ref = fields.Char(
        string="Referencia de la tienda", readonly=True, copy=False, index="btree_not_null",
        help="Referencia del pedido en la tienda en línea (creado por la API).",
    )

    _sql_constraints = [
        ("shop_external_ref_company_uniq", "unique(shop_external_ref, company_id)",
         "Ya existe un pedido de la tienda con esa referencia."),
    ]

    def _shop_api_serialize(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "external_ref": self.shop_external_ref,
            "state": self.state,
            "customer": {"id": self.partner_id.id, "name": self.partner_id.name, "vat": self.partner_id.vat},
            "amount_untaxed": self.amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "currency": self.currency_id.name,
            "lines": [
                {
                    "default_code": line.product_id.default_code,
                    "quantity": line.product_uom_qty,
                    "price_unit": line.price_unit,
                    "subtotal": line.price_subtotal,
                }
                for line in self.order_line.filtered(lambda l: not l.display_type)
            ],
        }
