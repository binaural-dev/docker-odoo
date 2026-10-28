from datetime import datetime, timezone

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

TRUE_VALUES = {"1", "true", "yes"}
FALSE_VALUES = {"0", "false", "no", ""}


class ShopApiError(Exception):
    """Error de la API con el formato que documentamos para la tienda."""

    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.field = field
        self.message = message

    def to_response(self):
        return request.make_json_response(
            {"error": {"code": self.code, "field": self.field, "message": self.message}},
            status=self.status,
        )


def _parse_datetime(value, field):
    """AAAA-MM-DD o AAAA-MM-DDTHH:MM:SS, opcionalmente con zona (Z, -04:00). Sin zona se toma como UTC."""
    text = value.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"  # fromisoformat no acepta «Z» antes de Python 3.11
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ShopApiError(
            400, "INVALID_DATE",
            f"La fecha «{value}» no es válida. Use AAAA-MM-DD o AAAA-MM-DDTHH:MM:SS (UTC), por ejemplo 2026-10-27T14:30:00.",
            field,
        ) from None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_bool(value, field):
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ShopApiError(400, "INVALID_PARAMETER", f"«{value}» no es válido. Use true o false.", field)


def _parse_category(value, field):
    try:
        category_id = int(value)
    except ValueError:
        raise ShopApiError(400, "INVALID_PARAMETER", f"«{value}» no es un id de categoría válido.", field) from None
    category = request.env["product.category"].browse(category_id).exists()
    if not category:
        raise ShopApiError(422, "CATEGORY_NOT_FOUND", f"No existe una categoría con el id {category_id}.", field)
    return category


class ShopApiController(http.Controller):

    @http.route("/api/v1/products", type="http", auth="user", methods=["GET"])
    def products(self, category_id=None, in_stock=None, updated_since=None, **_kwargs):
        try:
            Product = request.env["product.product"]
            domain = Product._shop_api_domain(
                category=_parse_category(category_id, "category_id") if category_id else None,
                in_stock=_parse_bool(in_stock, "in_stock") if in_stock is not None else False,
                updated_since=_parse_datetime(updated_since, "updated_since") if updated_since else None,
            )
            products = Product.search(domain, order="default_code, id")
            data = products._shop_api_serialize()
        except ShopApiError as error:
            return error.to_response()
        except AccessError:
            # La API usa los permisos del usuario de la integración (sin sudo): debe poder ver productos y stock.
            return ShopApiError(
                403, "FORBIDDEN",
                "El usuario de la integración no tiene permiso para consultar productos o inventario.",
            ).to_response()
        return request.make_json_response({
            "currency": request.env.company.currency_id.name,
            "count": len(products),
            "data": data,
        })
