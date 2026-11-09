import hashlib
import hmac
import json
import logging
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from odoo.addons.shop_integration_api.models.shop_webhook_event import MAX_ATTEMPTS, PARAM_SECRET, PARAM_URL

from .test_products_api import ShopApiCase

_logger = logging.getLogger(__name__)

REQUESTS_POST = "odoo.addons.shop_integration_api.models.shop_webhook_event.requests.post"


class TestPagination(ShopApiCase):
    """Tramo C: paginación con metadatos (total, página, siguiente)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.categ_page = cls.env["product.category"].create({"name": "Paginación"})
        cls.paged = [cls._product(f"PAG-{i}", f"Producto {i}", cls.categ_page, 10.0 + i, qty=1) for i in range(1, 6)]

    def test_pages_and_metadata(self):
        params = {"category_id": self.categ_page.id, "page_size": 2}
        seen = []
        page = 1
        while True:
            body = self._get({**params, "page": page}).json()
            self.assertEqual(body["total"], 5)
            self.assertEqual(body["page"], page)
            self.assertEqual(body["page_size"], 2)
            self.assertEqual(body["count"], len(body["data"]))
            seen += [item["default_code"] for item in body["data"]]
            if not body["next"]:
                break
            self.assertIn(f"page={page + 1}", body["next"])
            self.assertIn(f"category_id={self.categ_page.id}", body["next"], "next conserva los filtros")
            self.assertIn("page_size=2", body["next"])
            page += 1
        self.assertEqual(page, 3)
        self.assertEqual(seen, ["PAG-1", "PAG-2", "PAG-3", "PAG-4", "PAG-5"], "sin repetidos ni faltantes")

    def test_next_url_can_be_followed(self):
        body = self._get({"category_id": self.categ_page.id, "page_size": 4}).json()
        second = self.url_open(body["next"], headers=self._headers(self.api_key)).json()
        self.assertEqual([i["default_code"] for i in second["data"]], ["PAG-5"])
        self.assertIsNone(second["next"])

    def test_page_beyond_the_end_is_empty(self):
        body = self._get({"category_id": self.categ_page.id, "page": 9}).json()
        self.assertEqual(body["data"], [])
        self.assertEqual(body["total"], 5)
        self.assertIsNone(body["next"])

    def test_default_page_size(self):
        body = self._get({"category_id": self.categ_page.id}).json()
        self.assertEqual((body["page"], body["page_size"], body["next"]), (1, 50, None))

    def test_invalid_page_parameters(self):
        for params, field in [({"page": 0}, "page"), ({"page": "dos"}, "page"),
                              ({"page_size": 0}, "page_size"), ({"page_size": 201}, "page_size")]:
            self._assert_error(self._get(params), 400, "INVALID_PARAMETER", field)


@tagged("post_install", "-at_install")
class TestProductsQueryCount(TransactionCase):
    """Tramo C: el número de consultas del GET no crece con la cantidad de productos."""

    def _queries_for(self, n_products):
        category = self.env["product.category"].create({"name": f"Carga {n_products}"})
        location = self.env.ref("stock.warehouse0").lot_stock_id
        products = self.env["product.product"].create([
            {"name": f"P{n_products}-{i}", "default_code": f"Q{n_products}-{i:03d}", "categ_id": category.id,
             "is_storable": True, "list_price": 5.0}
            for i in range(n_products)
        ])
        for product in products:
            self.env["stock.quant"]._update_available_quantity(product, location, 3)
        Product = self.env["product.product"]
        domain = Product._shop_api_domain(category=category, in_stock=True, updated_since=fields.Datetime.now() - timedelta(days=1))
        Product._shop_api_page(domain, 1, 200)  # calentar: cachés del registro, no de los productos
        self.env.flush_all()
        self.env.invalidate_all()
        start = self.env.cr.sql_log_count
        result = Product._shop_api_page(domain, 1, 200)
        queries = self.env.cr.sql_log_count - start
        self.assertEqual(len(result["data"]), n_products)
        self.assertTrue(all(item["available_qty"] == 3 for item in result["data"]))
        return queries

    def test_query_count_does_not_grow(self):
        few, many = self._queries_for(5), self._queries_for(60)
        _logger.info("GET /api/v1/products: %s consultas con 5 productos, %s con 60", few, many)
        self.assertEqual(few, many, f"5 productos: {few} consultas; 60 productos: {many}")


class TestIdempotency(ShopApiCase):
    """Tramo C: cabecera Idempotency-Key en el POST."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.partner"].create({"name": "Cliente idempotencia", "vat": "J-55555555-5"})

    def _payload(self, ref="IDEM-1", qty=2):
        return {"customer_vat": "J-55555555-5", "external_ref": ref,
                "lines": [{"default_code": "SHOP-001", "quantity": qty}]}

    def _post_key(self, payload, key, raw=None):
        headers = {**self._headers(self.api_key), "Content-Type": "application/json", "Idempotency-Key": key}
        body = raw if raw is not None else json.dumps(payload)
        return self.url_open("/api/v1/orders", data=body, headers=headers)

    def _orders(self, ref):
        return self.env["sale.order"].search([("shop_external_ref", "=", ref)])

    def test_same_key_same_content_returns_same_order(self):
        first = self._post_key(self._payload(), "k-1")
        second = self._post_key(self._payload(), "k-1")
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.headers.get("Idempotent-Replayed"), "true")
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(second.json(), first.json())
        self.assertEqual(len(self._orders("IDEM-1")), 1)

    def test_same_content_with_keys_in_other_order_is_the_same(self):
        self._post_key(self._payload(), "k-order")
        raw = '{"lines": [{"quantity": 2, "default_code": "SHOP-001"}], "external_ref": "IDEM-1", "customer_vat": "J-55555555-5"}'
        response = self._post_key(None, "k-order", raw=raw)
        self.assertEqual(response.status_code, 200, response.text)

    def test_same_key_other_content_is_409(self):
        self.assertEqual(self._post_key(self._payload(), "k-2").status_code, 201)
        self._assert_error(self._post_key(self._payload(qty=3), "k-2"), 409, "IDEMPOTENCY_KEY_REUSED", "Idempotency-Key")
        self.assertEqual(len(self._orders("IDEM-1")), 1)
        self.assertEqual(self._orders("IDEM-1").order_line.product_uom_qty, 2.0)

    def test_failed_request_does_not_consume_the_key(self):
        bad = self._payload()
        bad["lines"][0]["default_code"] = "NO-EXISTE"
        self.assertEqual(self._post_key(bad, "k-3").status_code, 422)
        self.assertEqual(self._post_key(self._payload(), "k-3").status_code, 201)

    def test_keys_are_per_integration_user(self):
        other = new_test_user(
            self.env, login="shop_api_other", groups="base.group_user,sales_team.group_sale_salesman,stock.group_stock_user",
        )
        other_key = self._generate_key(other)
        self.assertEqual(self._post_key(self._payload("IDEM-A"), "shared").status_code, 201)
        headers = {**self._headers(other_key), "Content-Type": "application/json", "Idempotency-Key": "shared"}
        response = self.url_open("/api/v1/orders", data=json.dumps(self._payload("IDEM-B")), headers=headers)
        self.assertEqual(response.status_code, 201, response.text)

    def test_without_key_a_retry_is_a_duplicate(self):
        self.assertEqual(self._post(self._payload()).status_code, 201)
        self._assert_error(self._post(self._payload()), 409, "DUPLICATE_EXTERNAL_REF", "external_ref")

    def test_invalid_key(self):
        self._assert_error(self._post_key(self._payload(), "x" * 256), 400, "INVALID_IDEMPOTENCY_KEY", "Idempotency-Key")

    def test_key_is_not_stored_in_the_log_as_api_key(self):
        """El log no guarda la API key (la Idempotency-Key no es secreta y tampoco se registra)."""
        self._post_key(self._payload(), "k-log")
        self.env.cr.execute("SELECT row_to_json(l)::text FROM shop_api_log l")
        for (row,) in self.env.cr.fetchall():
            self.assertNotIn(self.api_key, row)


@tagged("post_install", "-at_install")
class TestDeliveryWebhook(TransactionCase):
    """Tramo C: aviso a la tienda al validar la entrega, con reintentos si la tienda no responde."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        params = cls.env["ir.config_parameter"].sudo()
        params.set_param(PARAM_URL, "https://tienda.test/webhooks/odoo")
        params.set_param(PARAM_SECRET, "secreto-de-prueba")
        cls.stock_user = new_test_user(
            cls.env, login="shop_wh_stock", groups="base.group_user,stock.group_stock_user,sales_team.group_sale_salesman",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente webhook"})
        cls.product = cls.env["product.product"].create({
            "name": "Producto webhook", "default_code": "WH-1", "is_storable": True, "list_price": 10.0,
        })
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.env.ref("stock.warehouse0").lot_stock_id, 10
        )

    def _confirmed_order(self, external_ref="WEB-W1"):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "shop_external_ref": external_ref,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
        })
        order.action_confirm()
        return order

    def _validate(self, order):
        picking = order.picking_ids.with_user(self.stock_user)
        picking.move_ids.write({"quantity": 2, "picked": True})
        self.assertIs(picking.button_validate(), True)
        self.assertEqual(picking.state, "done")
        return picking

    def _events(self, order):
        return self.env["shop.webhook.event"].search([("order_id", "=", order.id)])

    def _run_cron(self):
        self.env["shop.webhook.event"]._cron_send_pending()

    def _make_due(self, events):
        events.write({"next_attempt_at": fields.Datetime.now() - timedelta(seconds=1)})

    def test_validation_only_enqueues(self):
        order = self._confirmed_order()
        with patch(REQUESTS_POST) as post:
            picking = self._validate(order)
        post.assert_not_called()  # quien valida nunca espera a la tienda
        event = self._events(order)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.state, "pending")
        payload = json.loads(event.payload)
        self.assertEqual(payload["event"], "order.delivered")
        self.assertEqual(payload["event_id"], event.id)
        self.assertEqual(payload["order"]["external_ref"], "WEB-W1")
        self.assertEqual(payload["delivery"]["name"], picking.name)
        self.assertEqual(payload["lines"], [{"default_code": "WH-1", "quantity": 2.0}])
        self.assertRegex(payload["occurred_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_cron_sends_signed_event(self):
        order = self._confirmed_order()
        self._validate(order)
        event = self._events(order)
        with patch(REQUESTS_POST, return_value=MagicMock(status_code=200)) as post:
            self._run_cron()
        self.assertEqual(event.state, "sent")
        self.assertEqual(event.attempts, 1)
        _args, kwargs = post.call_args
        self.assertEqual(post.call_args.args[0], "https://tienda.test/webhooks/odoo")
        self.assertEqual(kwargs["timeout"], 10)
        expected = hmac.new(b"secreto-de-prueba", kwargs["data"], hashlib.sha256).hexdigest()
        self.assertEqual(kwargs["headers"]["X-Shop-Signature"], f"sha256={expected}")
        self.assertEqual(kwargs["headers"]["X-Shop-Event-Id"], str(event.id))

    def test_store_down_does_not_affect_validation_and_retries(self):
        order = self._confirmed_order()
        with patch(REQUESTS_POST, side_effect=requests.ConnectionError("caída")):
            picking = self._validate(order)  # no falla: no llama a la tienda
            self._run_cron()
        self.assertEqual(picking.state, "done")
        event = self._events(order)
        self.assertEqual(event.state, "pending")
        self.assertEqual(event.attempts, 1)
        self.assertIn("No se pudo conectar", event.last_error)
        self.assertGreater(event.next_attempt_at, fields.Datetime.now() + timedelta(seconds=50))
        with patch(REQUESTS_POST) as post:
            self._run_cron()  # todavía no toca: no reintenta antes de tiempo
        post.assert_not_called()

    def test_retries_with_growing_delays_then_fails(self):
        order = self._confirmed_order()
        self._validate(order)
        event = self._events(order)
        delays = []
        with patch(REQUESTS_POST, return_value=MagicMock(status_code=503)):
            for _attempt in range(MAX_ATTEMPTS):
                self._make_due(event)
                before = fields.Datetime.now()
                self._run_cron()
                if event.state == "pending":
                    delays.append(round((event.next_attempt_at - before).total_seconds() / 60))
        self.assertEqual(event.state, "failed")
        self.assertEqual(event.attempts, MAX_ATTEMPTS)
        self.assertEqual(event.last_status_code, 503)
        self.assertEqual(delays, [1, 5, 15, 30, 60, 120, 240])

    def test_recovers_after_store_comes_back(self):
        order = self._confirmed_order()
        self._validate(order)
        event = self._events(order)
        with patch(REQUESTS_POST, side_effect=requests.Timeout()):
            self._run_cron()
        self._make_due(event)
        with patch(REQUESTS_POST, return_value=MagicMock(status_code=204)):
            self._run_cron()
        self.assertEqual((event.state, event.attempts), ("sent", 2))

    def test_only_shop_orders_and_only_deliveries(self):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
        })
        order.action_confirm()
        self._validate(order)
        self.assertFalse(self._events(order), "Un pedido que no viene de la tienda no genera aviso")

    def test_no_url_no_events(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_URL, "")
        order = self._confirmed_order("WEB-NOURL")
        self._validate(order)
        self.assertFalse(self._events(order))

    def test_enqueue_failure_does_not_break_validation(self):
        order = self._confirmed_order("WEB-BROKEN")
        with patch.object(type(self.env["shop.webhook.event"]), "_enqueue_deliveries", side_effect=Exception("bug")), \
                self.assertLogs("odoo.addons.shop_integration_api.models.stock_picking", level="ERROR"):
            picking = self._validate(order)
        self.assertEqual(picking.state, "done")

    def test_retry_now_button(self):
        order = self._confirmed_order()
        self._validate(order)
        event = self._events(order)
        event.write({"state": "failed"})
        event.action_retry_now()
        self.assertEqual(event.state, "pending")
        self.assertLessEqual(event.next_attempt_at, fields.Datetime.now())
