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

    @api.model
    def _shop_api_page(self, domain, page=1, page_size=50):
        """Una página de productos con sus metadatos.

        La cantidad de consultas no depende de cuántos productos haya en la página: una para el total, una
        para la página y lecturas en lote (nombre, precio y stock se calculan para todo el lote junto, no
        producto por producto). Lo verifica test_query_count_does_not_grow.
        """
        total = self.search_count(domain)
        products = self.search(domain, order="default_code, id", limit=page_size, offset=(page - 1) * page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": page * page_size < total,
            "data": products._shop_api_serialize(),
        }

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
