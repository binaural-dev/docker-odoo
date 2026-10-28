import json
import logging
import re
import time
from datetime import datetime, timezone

from psycopg2 import IntegrityError

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes"}
FALSE_VALUES = {"0", "false", "no", ""}
BEARER_RE = re.compile(r"^bearer\s+(\S+)\s*$", re.IGNORECASE)


class ShopApiError(Exception):
    """Error de la API con el formato que documentamos para la tienda."""

    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.field = field
        self.message = message

    def to_response(self):
        headers = [("WWW-Authenticate", 'Bearer realm="odoo"')] if self.status == 401 else None
        return request.make_json_response(
            {"error": {"code": self.code, "field": self.field, "message": self.message}},
            headers=headers, status=self.status,
        )


# Parámetros del GET

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


# Cuerpo del POST

def _require_text(payload, key):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ShopApiError(422, "MISSING_FIELD", f"El campo «{key}» es obligatorio y debe ser un texto.", key)
    return value.strip()


def _parse_order_payload(body):
    """Valida el JSON del pedido y lo traduce a registros. Devuelve (cliente, referencia, [(producto, cantidad)])."""
    try:
        payload = json.loads(body or b"")
    except (ValueError, UnicodeDecodeError):
        raise ShopApiError(400, "INVALID_JSON", "El cuerpo de la petición no es un JSON válido.") from None
    if not isinstance(payload, dict):
        raise ShopApiError(400, "INVALID_JSON", "El cuerpo debe ser un objeto JSON.")

    vat = _require_text(payload, "customer_vat")
    external_ref = _require_text(payload, "external_ref")
    customers = request.env["res.partner"]._shop_api_find_by_vat(vat)
    if not customers:
        raise ShopApiError(422, "CUSTOMER_NOT_FOUND", f"No existe un cliente con el RIF {vat}.", "customer_vat")
    if len(customers) > 1:
        raise ShopApiError(
            422, "AMBIGUOUS_CUSTOMER", f"Hay más de un cliente con el RIF {vat}. Avise a la empresa para depurarlo.",
            "customer_vat",
        )

    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ShopApiError(422, "MISSING_FIELD", "El pedido debe tener al menos una línea en «lines».", "lines")
    Product = request.env["product.product"]
    parsed_lines = []
    for index, line in enumerate(lines):
        prefix = f"lines[{index}]"
        if not isinstance(line, dict):
            raise ShopApiError(422, "INVALID_LINE", "Cada línea debe ser un objeto JSON.", prefix)
        code = line.get("default_code")
        if not isinstance(code, str) or not code.strip():
            raise ShopApiError(422, "MISSING_FIELD", "Falta el código del producto.", f"{prefix}.default_code")
        quantity = line.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
            raise ShopApiError(422, "INVALID_QUANTITY", "La cantidad debe ser un número.", f"{prefix}.quantity")
        if quantity <= 0:
            raise ShopApiError(
                422, "INVALID_QUANTITY", f"La cantidad debe ser mayor que cero (recibido: {quantity}).",
                f"{prefix}.quantity",
            )
        product = Product.search([("default_code", "=", code.strip()), ("sale_ok", "=", True)])
        if not product:
            raise ShopApiError(
                422, "PRODUCT_NOT_FOUND", f"No existe un producto con el código {code}.", f"{prefix}.default_code"
            )
        if len(product) > 1:
            raise ShopApiError(
                422, "AMBIGUOUS_PRODUCT", f"Hay más de un producto con el código {code}.", f"{prefix}.default_code"
            )
        parsed_lines.append((product, quantity))
    return customers, external_ref, parsed_lines


class ShopApiController(http.Controller):

    def _authenticate(self):
        """API key nativa de Odoo (res.users.apikeys, alcance rpc) en «Authorization: Bearer <clave>»."""
        header = request.httprequest.headers.get("Authorization", "")
        match = BEARER_RE.match(header)
        if not match:
            raise ShopApiError(401, "UNAUTHORIZED", "Falta la cabecera «Authorization: Bearer <API key>».")
        uid = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=match.group(1))
        if not uid:
            raise ShopApiError(401, "INVALID_API_KEY", "La API key no es válida, venció o el usuario está inactivo.")
        request.update_env(user=uid)
        return uid

    def _handle(self, endpoint, handler):
        """Autentica, ejecuta y registra la llamada (también las que fallan). Nunca guarda la API key."""
        start = time.perf_counter()
        log_vals = {"endpoint": endpoint, "method": request.httprequest.method}
        try:
            log_vals["user_id"] = self._authenticate()
            # Savepoint: si la llamada falla, se deshace lo que alcanzó a escribir y el log igual se guarda.
            with request.env.cr.savepoint():
                response = handler(log_vals)
        except ShopApiError as error:
            response = error.to_response()
            log_vals["error_code"] = error.code
        except AccessError:
            # La API usa los permisos del usuario de la integración (sin sudo).
            error = ShopApiError(403, "FORBIDDEN", "El usuario de la integración no tiene permiso para esta operación.")
            response = error.to_response()
            log_vals["error_code"] = error.code
        except UserError as user_error:
            # Reglas de negocio de Odoo al crear o confirmar el pedido.
            error = ShopApiError(422, "BUSINESS_RULE", str(user_error))
            response = error.to_response()
            log_vals["error_code"] = error.code
        except Exception:
            _logger.exception("Error inesperado en %s", endpoint)
            error = ShopApiError(500, "INTERNAL_ERROR", "Error interno. Intente de nuevo o avise a la empresa.")
            response = error.to_response()
            log_vals["error_code"] = error.code
        log_vals.update({
            "status_code": response.status_code,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "remote_addr": request.httprequest.remote_addr,
        })
        # sudo(): el usuario de la integración no tiene (ni debe tener) acceso al registro de llamadas.
        request.env["shop.api.log"].sudo().create(log_vals)
        return response

    # readonly=False: Odoo 18 abre los GET con un cursor de solo lectura. Como cada llamada escribe su log,
    # Odoo reintentaría la petición completa con otro cursor (se ejecutaría dos veces).
    @http.route("/api/v1/products", type="http", auth="none", methods=["GET"], csrf=False, readonly=False)
    def products(self, category_id=None, in_stock=None, updated_since=None, **_kwargs):
        def handler(_log_vals):
            Product = request.env["product.product"]
            domain = Product._shop_api_domain(
                category=_parse_category(category_id, "category_id") if category_id else None,
                in_stock=_parse_bool(in_stock, "in_stock") if in_stock is not None else False,
                updated_since=_parse_datetime(updated_since, "updated_since") if updated_since else None,
            )
            products = Product.search(domain, order="default_code, id")
            return request.make_json_response({
                "currency": request.env.company.currency_id.name,
                "count": len(products),
                "data": products._shop_api_serialize(),
            })

        return self._handle("/api/v1/products", handler)

    @http.route("/api/v1/orders", type="http", auth="none", methods=["POST"], csrf=False, readonly=False)
    def create_order(self, **_kwargs):
        def handler(log_vals):
            customer, external_ref, lines = _parse_order_payload(request.httprequest.get_data())
            log_vals["external_ref"] = external_ref
            SaleOrder = request.env["sale.order"]
            existing = SaleOrder.search([
                ("shop_external_ref", "=", external_ref), ("company_id", "=", request.env.company.id),
            ], limit=1)
            if existing:
                raise ShopApiError(
                    409, "DUPLICATE_EXTERNAL_REF",
                    f"Ya existe el pedido {existing.name} con la referencia {external_ref}.", "external_ref",
                )
            try:
                with request.env.cr.savepoint():
                    order = SaleOrder.create({
                        "partner_id": customer.id,
                        "client_order_ref": external_ref,
                        "shop_external_ref": external_ref,
                        "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": quantity})
                                       for product, quantity in lines],
                    })
                    order.flush_recordset()
            except IntegrityError:
                # Dos llamadas simultáneas con la misma referencia: la restricción única decide.
                raise ShopApiError(
                    409, "DUPLICATE_EXTERNAL_REF", f"Ya existe un pedido con la referencia {external_ref}.",
                    "external_ref",
                ) from None
            order.action_confirm()
            log_vals["order_id"] = order.id
            return request.make_json_response(order._shop_api_serialize(), status=201)

        return self._handle("/api/v1/orders", handler)
