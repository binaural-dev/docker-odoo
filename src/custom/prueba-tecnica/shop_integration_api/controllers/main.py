import logging
from datetime import datetime

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ShopApiController(http.Controller):
    @http.route(
        "/api/v1/products",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def get_products(self, **params):
        """Devuelve el catálogo de productos activos y vendibles en formato JSON.

        Parámetros soportados vía query string:
        - category_id: ID entero de la categoría (product.category).
        - only_stock: 'true'/'1' para incluir únicamente productos con stock disponible (> 0).
        - updated_since: Fecha/hora en formato ISO-8601 (ej. YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS).
        """
        domain = [("active", "=", True), ("sale_ok", "=", True)]

        # Filtro: category_id
        category_id = params.get("category_id")
        if category_id:
            try:
                category_id = int(category_id)
                domain.append(("categ_id", "=", category_id))
            except (ValueError, TypeError):
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_FILTER",
                            "field": "category_id",
                            "message": "El parámetro category_id debe ser un número entero válido.",
                        }
                    },
                    status=422,
                )

        # Filtro: only_stock
        only_stock = params.get("only_stock")
        if only_stock is not None:
            val = str(only_stock).strip().lower()
            if val in ("true", "1", "yes", "t"):
                domain.append(("qty_available", ">", 0))

        # Filtro: updated_since
        updated_since = params.get("updated_since")
        if updated_since:
            parsed_dt = None
            try:
                # Intento de parseo estándar ISO-8601
                parsed_dt = datetime.fromisoformat(updated_since)
            except (ValueError, TypeError):
                try:
                    parsed_dt = fields.Datetime.to_datetime(updated_since)
                except Exception:
                    parsed_dt = None

            if not parsed_dt:
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_FILTER",
                            "field": "updated_since",
                            "message": (
                                "Formato de fecha inválido. "
                                "Use formato ISO-8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)."
                            ),
                        }
                    },
                    status=422,
                )

            domain.append(("write_date", ">=", parsed_dt))

        try:
            products = request.env["product.product"].search(domain, order="id asc")
            result = [
                {
                    "id": p.id,
                    "code": p.default_code or "",
                    "name": p.name,
                    "price": float(p.list_price),
                    "qty_available": float(p.sudo().qty_available) if hasattr(p, "qty_available") else 0.0,
                }
                for p in products
            ]
            return request.make_json_response(result, status=200)

        except Exception as e:
            _logger.exception("Error al consultar el catálogo de productos: %s", str(e))
            return request.make_json_response(
                {
                    "error": {
                        "code": "SERVER_ERROR",
                        "message": "Ocurrió un error inesperado al procesar la solicitud.",
                    }
                },
                status=500,
            )

