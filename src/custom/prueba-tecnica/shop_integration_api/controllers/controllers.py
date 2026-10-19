import hashlib
import json
import logging
import time
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ShopIntegrationApiController(http.Controller):

    def _make_error(self, code, field, message, status=422):
        payload = {
            "error": {
                "code": code,
                "field": field,
                "message": message,
            }
        }
        return request.make_json_response(payload, status=status)

    def _log_call(self, endpoint, user_id, status_code, start_time):
        """Registra la llamada sin almacenar claves secretas."""
        duration = time.time() - start_time
        try:
            request.env['shop.api.log'].sudo().create({
                'endpoint': endpoint,
                'user_id': user_id or False,
                'response_code': status_code,
                'duration': round(duration, 4),
            })
        except Exception as e:
            _logger.warning("No se pudo registrar log de API: %s", e)

    def _authenticate_bearer(self):
        """Valida la cabecera Authorization: Bearer <key> contra res.users.apikeys."""
        auth_header = request.httprequest.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, "Cabecera Authorization con formato 'Bearer <clave>' requerida."

        api_key = auth_header.split('Bearer ', 1)[1].strip()
        if not api_key:
            return None, "Clave de API ausente."

        Apikeys = request.env['res.users.apikeys'].sudo()
        try:
            # En Odoo 19 el scope obligatorio para claves API es 'rpc'
            user_id = Apikeys._check_credentials(scope='rpc', key=api_key)
        except Exception:
            user_id = None

        if not user_id:
            return None, "Clave de API inválida o expirada."

        return user_id, None

    def _parse_datetime(self, date_str):
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @http.route('/api/v1/products', type='http', auth='user', methods=['GET'], csrf=False)
    def get_products(self, **kwargs):
        domain = [('sale_ok', '=', True), ('active', '=', True)]

        category_param = kwargs.get('category') or kwargs.get('category_id')
        if category_param:
            if category_param.isdigit():
                domain.append(('categ_id', '=', int(category_param)))
            else:
                domain.append(('categ_id.name', 'ilike', category_param))

        only_stock = kwargs.get('only_stock') or kwargs.get('in_stock')
        if only_stock and only_stock.lower() in ('true', '1', 'yes'):
            domain.append(('qty_available', '>', 0))

        modified_since = kwargs.get('modified_since')
        if modified_since:
            parsed_date = self._parse_datetime(modified_since)
            if not parsed_date:
                return self._make_error(
                    "INVALID_DATE_FORMAT",
                    "modified_since",
                    "Formato de fecha inválido. Utilice formato ISO (ej. YYYY-MM-DD).",
                    status=400
                )
            domain.append(('write_date', '>=', parsed_date))

        products = request.env['product.product'].search(domain)
        data = [
            {
                'id': p.id,
                'code': p.default_code or '',
                'name': p.name,
                'price': p.list_price,
                'qty_available': p.qty_available,
            }
            for p in products
        ]
        return request.make_json_response(data, status=200)

    @http.route('/api/v1/orders', type='http', auth='none', methods=['POST'], csrf=False, readonly=False)
    def create_order(self, **kwargs):
        start_time = time.time()
        endpoint = '/api/v1/orders'

        user_id, auth_error = self._authenticate_bearer()
        if not user_id:
            self._log_call(endpoint, False, 401, start_time)
            return self._make_error("UNAUTHORIZED", "Authorization", auth_error, status=401)

        try:
            raw_body = request.httprequest.data
            payload = json.loads(raw_body.decode('utf-8'))
        except Exception:
            self._log_call(endpoint, user_id, 400, start_time)
            return self._make_error("MALFORMED_JSON", "body", "El cuerpo de la petición no es un JSON válido.", status=400)

        idempotency_key = request.httprequest.headers.get('Idempotency-Key')
        body_hash = hashlib.sha256(raw_body).hexdigest()
        IdempModel = request.env['shop.idempotency.key'].sudo()

        if idempotency_key:
            existing = IdempModel.search([('key', '=', idempotency_key)], limit=1)
            if existing:
                if existing.request_hash == body_hash:
                    self._log_call(endpoint, user_id, existing.response_code, start_time)
                    return request.make_json_response(json.loads(existing.response_body), status=existing.response_code)
                else:
                    self._log_call(endpoint, user_id, 409, start_time)
                    return self._make_error(
                        "IDEMPOTENCY_CONFLICT",
                        "Idempotency-Key",
                        "La clave de idempotencia ya fue utilizada con un contenido diferente.",
                        status=409
                    )

        rif = payload.get('rif')
        if not rif:
            self._log_call(endpoint, user_id, 422, start_time)
            return self._make_error("MISSING_FIELD", "rif", "El campo RIF es obligatorio.", status=422)

        partner = request.env['res.partner'].with_user(user_id).search([('vat', '=', rif)], limit=1)
        if not partner:
            self._log_call(endpoint, user_id, 422, start_time)
            return self._make_error("PARTNER_NOT_FOUND", "rif", f"No existe un cliente con el RIF {rif}", status=422)

        lines_data = payload.get('lines')
        if not lines_data or not isinstance(lines_data, list):
            self._log_call(endpoint, user_id, 422, start_time)
            return self._make_error("MISSING_FIELD", "lines", "Debe incluir una lista de líneas.", status=422)

        order_lines = []
        for idx, line in enumerate(lines_data):
            code = line.get('default_code')
            qty = line.get('quantity')

            product = request.env['product.product'].with_user(user_id).search([
                ('default_code', '=', code),
                ('sale_ok', '=', True),
                ('active', '=', True),
            ], limit=1)

            if not product:
                self._log_call(endpoint, user_id, 422, start_time)
                return self._make_error(
                    "PRODUCT_NOT_FOUND",
                    f"lines[{idx}].default_code",
                    f"No existe un producto con el código {code}",
                    status=422
                )

            if qty is None or qty <= 0:
                self._log_call(endpoint, user_id, 422, start_time)
                return self._make_error(
                    "INVALID_QUANTITY",
                    f"lines[{idx}].quantity",
                    f"La cantidad debe ser mayor a 0. Recibido: {qty}",
                    status=422
                )

            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
            }))

        order_vals = {
            'partner_id': partner.id,
            'client_order_ref': payload.get('client_order_ref', ''),
            'user_id': user_id,
            'order_line': order_lines,
        }
        order = request.env['sale.order'].with_user(user_id).create(order_vals)

        response_payload = {
            "order_id": order.id,
            "name": order.name,
            "client_order_ref": order.client_order_ref,
            "state": order.state,
            "amount_total": order.amount_total,
        }

        if idempotency_key:
            IdempModel.create({
                'key': idempotency_key,
                'request_hash': body_hash,
                'response_code': 201,
                'response_body': json.dumps(response_payload),
                'order_id': order.id,
            })

        self._log_call(endpoint, user_id, 201, start_time)
        return request.make_json_response(response_payload, status=201)