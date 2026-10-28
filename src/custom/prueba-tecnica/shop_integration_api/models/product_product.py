from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _shop_api_domain(self, category=None, in_stock=False, updated_since=None):
        """Dominio de los productos que ve la tienda: activos (por defecto) y que se pueden vender."""
        domain = [("sale_ok", "=", True)]
        if category:
            domain.append(("categ_id", "child_of", category.id))
        if in_stock:
            domain.append(("free_qty", ">", 0))
        if updated_since:
            # Precio y nombre viven en la plantilla: un cambio ahí no toca el write_date de la variante.
            domain += [
                "|",
                ("write_date", ">=", updated_since),
                ("product_tmpl_id.write_date", ">=", updated_since),
            ]
        return domain

    def _shop_api_serialize(self):
        """Datos de cada producto para la tienda. free_qty se calcula para todo el lote junto."""
        # Nombre con los valores de la variante (p. ej. «Camisa (Rojo, M)») pero sin el código delante.
        products = self.with_context(display_default_code=False)
        return [
            {
                "id": product.id,
                "default_code": product.default_code or None,
                "name": product.display_name,
                "price": product.lst_price,
                "available_qty": product.free_qty,
            }
            for product in products
        ]
