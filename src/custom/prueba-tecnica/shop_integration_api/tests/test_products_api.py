import json

from odoo.exceptions import AccessError

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

PRODUCTS_URL = "/api/v1/products"
ORDERS_URL = "/api/v1/orders"


@tagged("post_install", "-at_install")
class ShopApiCase(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Usuario dedicado a la integración, con los permisos mínimos para ver productos, stock y vender.
        cls.api_user = new_test_user(
            cls.env, login="shop_api_user", name="Tienda en línea",
            groups="base.group_user,sales_team.group_sale_salesman,stock.group_stock_user",
        )
        cls.api_key = cls._generate_key(cls.api_user)
        cls.no_stock_user = new_test_user(cls.env, login="shop_api_nostock", groups="base.group_user")
        cls.no_stock_key = cls._generate_key(cls.no_stock_user)

        cls.stock_location = cls.env.ref("stock.warehouse0").lot_stock_id
        cls.categ_shop = cls.env["product.category"].create({"name": "Tienda"})
        cls.categ_shop_child = cls.env["product.category"].create({"name": "Accesorios", "parent_id": cls.categ_shop.id})
        cls.categ_other = cls.env["product.category"].create({"name": "Otra"})

        cls.p_stock = cls._product("SHOP-001", "Mouse", cls.categ_shop, 25.0, qty=10)
        cls.p_no_stock = cls._product("SHOP-002", "Cable USB", cls.categ_shop_child, 5.0, qty=0)
        cls.p_other = cls._product("SHOP-003", "Silla", cls.categ_other, 80.0, qty=3)
        cls.p_not_sellable = cls._product("SHOP-004", "Repuesto interno", cls.categ_shop, 1.0, qty=7, sale_ok=False)
        cls.p_archived = cls._product("SHOP-005", "Modelo viejo", cls.categ_shop, 9.0, qty=2)
        cls.p_archived.active = False

        # «Silla» no se toca desde 2020 (ni la variante ni la plantilla).
        cls._set_write_date(cls.p_other, "2020-01-01 00:00:00")

    @classmethod
    def _generate_key(cls, user):
        # sudo() solo en la preparación: un usuario no administrador debe poner fecha de vencimiento a su clave.
        return cls.env["res.users.apikeys"].with_user(user).sudo()._generate("rpc", "Tienda en línea", None)

    @classmethod
    def _product(cls, code, name, categ, price, qty=0, sale_ok=True):
        product = cls.env["product.product"].create({
            "name": name, "default_code": code, "categ_id": categ.id, "list_price": price,
            "is_storable": True, "sale_ok": sale_ok, "taxes_id": [(5, 0, 0)],
        })
        if qty:
            cls.env["stock.quant"]._update_available_quantity(product, cls.stock_location, qty)
        return product

    @classmethod
    def _set_write_date(cls, product, value):
        cls.env.flush_all()
        cls.env.cr.execute("UPDATE product_product SET write_date = %s WHERE id = %s", (value, product.id))
        cls.env.cr.execute(
            "UPDATE product_template SET write_date = %s WHERE id = %s", (value, product.product_tmpl_id.id)
        )
        cls.env.invalidate_all()

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _get(self, params=None, key=True):
        key = self.api_key if key is True else key
        query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        url = f"{PRODUCTS_URL}?{query}" if query else PRODUCTS_URL
        return self.url_open(url, headers=self._headers(key), allow_redirects=False)

    def _post(self, payload, key=True, raw=None):
        key = self.api_key if key is True else key
        headers = {**self._headers(key), "Content-Type": "application/json"}
        body = raw if raw is not None else json.dumps(payload)
        return self.url_open(ORDERS_URL, data=body, headers=headers, allow_redirects=False)

    def _ids(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return {item["id"] for item in response.json()["data"]}

    def _assert_error(self, response, status, code, field):
        self.assertEqual(response.status_code, status, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        self.assertEqual(error["field"], field)
        self.assertTrue(error["message"])
        return error


class TestProductsApi(ShopApiCase):
    """Tramo A: GET /api/v1/products (ahora con API key)."""

    def test_response_fields(self):
        body = self._get({"category_id": self.categ_shop.id}).json()
        self.assertEqual(body["currency"], self.env.company.currency_id.name)
        item = next(i for i in body["data"] if i["id"] == self.p_stock.id)
        self.assertEqual(item, {
            "id": self.p_stock.id, "default_code": "SHOP-001", "name": "Mouse", "price": 25.0, "available_qty": 10.0,
        })
        self.assertEqual(body["count"], len(body["data"]))

    def test_only_active_and_sellable(self):
        ids = self._ids(self._get())
        self.assertTrue({self.p_stock.id, self.p_no_stock.id, self.p_other.id} <= ids)
        self.assertNotIn(self.p_not_sellable.id, ids)
        self.assertNotIn(self.p_archived.id, ids)

    def test_filter_category_includes_children(self):
        ids = self._ids(self._get({"category_id": self.categ_shop.id}))
        self.assertEqual(ids, {self.p_stock.id, self.p_no_stock.id})

    def test_filter_in_stock(self):
        ids = self._ids(self._get({"in_stock": "true"}))
        self.assertIn(self.p_stock.id, ids)
        self.assertIn(self.p_other.id, ids)
        self.assertNotIn(self.p_no_stock.id, ids)
        self.assertIn(self.p_no_stock.id, self._ids(self._get({"in_stock": "false"})))

    def test_filter_updated_since(self):
        ids = self._ids(self._get({"updated_since": "2024-01-01"}))
        self.assertIn(self.p_stock.id, ids)
        self.assertNotIn(self.p_other.id, ids)
        self.assertIn(self.p_other.id, self._ids(self._get({"updated_since": "2019-12-31T23:00:00Z"})))
        # Con zona horaria: 2020-01-01 00:00 UTC son las 20:00 del 31/12 en Venezuela (-04:00).
        self.assertIn(self.p_other.id, self._ids(self._get({"updated_since": "2019-12-31T20:00:00-04:00"})))
        self.assertNotIn(self.p_other.id, self._ids(self._get({"updated_since": "2019-12-31T20:00:01-04:00"})))

    def test_updated_since_sees_template_changes(self):
        """Cambiar el precio (campo de la plantilla) cuenta como modificación del producto."""
        self.p_other.product_tmpl_id.list_price = 85.0
        self.env.flush_all()
        self.assertIn(self.p_other.id, self._ids(self._get({"updated_since": "2024-01-01"})))

    def test_filters_combined(self):
        self.assertEqual(self._ids(self._get({"category_id": self.categ_shop.id, "in_stock": "1"})), {self.p_stock.id})
        params = {"category_id": self.categ_other.id, "in_stock": "1", "updated_since": "2024-01-01"}
        self.assertEqual(self._ids(self._get(params)), set())
        params["updated_since"] = "2019-01-01"
        self.assertEqual(self._ids(self._get(params)), {self.p_other.id})

    def test_invalid_date(self):
        for value in ("27/10/2026", "2026-13-01", "ayer", "2026-10-27T25:00:00"):
            error = self._assert_error(self._get({"updated_since": value}), 400, "INVALID_DATE", "updated_since")
            self.assertIn(value, error["message"])

    def test_invalid_category(self):
        self._assert_error(self._get({"category_id": "abc"}), 400, "INVALID_PARAMETER", "category_id")
        self._assert_error(self._get({"category_id": "999999"}), 422, "CATEGORY_NOT_FOUND", "category_id")

    def test_invalid_in_stock(self):
        self._assert_error(self._get({"in_stock": "quizas"}), 400, "INVALID_PARAMETER", "in_stock")

    def test_user_without_stock_rights(self):
        """Sin permisos de inventario: 403 claro con el formato de la API, no un error genérico."""
        self._assert_error(self._get(key=self.no_stock_key), 403, "FORBIDDEN", None)

    def test_only_get(self):
        response = self.url_open(PRODUCTS_URL, data={"x": "1"}, headers=self._headers(self.api_key))
        self.assertEqual(response.status_code, 405)

    def test_response_is_json(self):
        response = self._get()
        self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
        json.loads(response.text)


class TestApiAuthentication(ShopApiCase):
    """Tramo B: API keys nativas en Authorization: Bearer."""

    def test_missing_key_is_401(self):
        for response in (self._get(key=None), self._post({}, key=None)):
            self._assert_error(response, 401, "UNAUTHORIZED", None)
            self.assertIn("Bearer", response.headers.get("WWW-Authenticate", ""))

    def test_invalid_key_is_401(self):
        for key in ("no-es-una-clave", self.api_key[:-1] + ("x" if self.api_key[-1] != "x" else "y")):
            self._assert_error(self._get(key=key), 401, "INVALID_API_KEY", None)
            self._assert_error(self._post({}, key=key), 401, "INVALID_API_KEY", None)

    def test_wrong_scheme_is_401(self):
        response = self.url_open(PRODUCTS_URL, headers={"Authorization": f"Basic {self.api_key}"})
        self._assert_error(response, 401, "UNAUTHORIZED", None)

    def test_session_is_not_enough(self):
        """Una sesión de navegador no reemplaza la API key."""
        self.authenticate("shop_api_user", "shop_api_user")
        self._assert_error(self._get(key=None), 401, "UNAUTHORIZED", None)

    def test_archived_user_key_is_401(self):
        self.api_user.active = False
        self._assert_error(self._get(), 401, "INVALID_API_KEY", None)

    def test_key_acts_as_its_user(self):
        response = self._post({"customer_vat": "X", "external_ref": "R", "lines": []})
        log = self.env["shop.api.log"].search([], limit=1)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(log.user_id, self.api_user)


class TestOrdersApi(ShopApiCase):
    """Tramo B: POST /api/v1/orders."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({
            "name": "Comercial Los Andes C.A.", "vat": "J-12345678-9", "is_company": True,
        })
        cls.env["res.partner"].create({"name": "Contacto de compras", "parent_id": cls.customer.id})

    def _payload(self, **overrides):
        payload = {
            "customer_vat": "J-12345678-9",
            "external_ref": "WEB-1001",
            "lines": [{"default_code": "SHOP-001", "quantity": 2}, {"default_code": "SHOP-003", "quantity": 1}],
        }
        payload.update(overrides)
        return payload

    def _orders(self, ref="WEB-1001"):
        return self.env["sale.order"].search([("shop_external_ref", "=", ref)])

    def test_create_order(self):
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        order = self._orders()
        self.assertEqual(len(order), 1)
        self.assertEqual(body["id"], order.id)
        self.assertEqual(body["name"], order.name)
        self.assertEqual(body["external_ref"], "WEB-1001")
        self.assertEqual(body["state"], "sale", "Supuesto: el pedido queda confirmado")
        self.assertEqual(order.partner_id, self.customer)
        self.assertEqual(order.client_order_ref, "WEB-1001")
        self.assertEqual(order.user_id, self.api_user)
        self.assertEqual(
            [(l.product_id.default_code, l.product_uom_qty) for l in order.order_line],
            [("SHOP-001", 2.0), ("SHOP-003", 1.0)],
        )
        self.assertAlmostEqual(body["amount_total"], 2 * 25.0 + 80.0)
        self.assertTrue(order.picking_ids, "Confirmado: genera la entrega")

    def test_vat_is_normalized(self):
        for i, vat in enumerate(("J123456789", "j-12345678-9", " J 12345678 9 ")):
            response = self._post(self._payload(customer_vat=vat, external_ref=f"WEB-N{i}"))
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["customer"]["id"], self.customer.id)

    def test_customer_not_found(self):
        self._assert_error(self._post(self._payload(customer_vat="V-99999999")), 422, "CUSTOMER_NOT_FOUND", "customer_vat")

    def test_product_not_found_points_to_line(self):
        lines = [{"default_code": "SHOP-001", "quantity": 1}, {"default_code": "ABC-123", "quantity": 1}]
        error = self._assert_error(
            self._post(self._payload(lines=lines)), 422, "PRODUCT_NOT_FOUND", "lines[1].default_code"
        )
        self.assertIn("ABC-123", error["message"])

    def test_not_sellable_product_is_not_found(self):
        lines = [{"default_code": "SHOP-004", "quantity": 1}]
        self._assert_error(self._post(self._payload(lines=lines)), 422, "PRODUCT_NOT_FOUND", "lines[0].default_code")

    def test_invalid_quantities(self):
        for quantity in (0, -1, -0.5, "2", None, True):
            lines = [{"default_code": "SHOP-001", "quantity": 1}, {"default_code": "SHOP-003", "quantity": quantity}]
            self._assert_error(
                self._post(self._payload(lines=lines)), 422, "INVALID_QUANTITY", "lines[1].quantity"
            )

    def test_missing_fields(self):
        self._assert_error(self._post(self._payload(customer_vat="")), 422, "MISSING_FIELD", "customer_vat")
        self._assert_error(self._post(self._payload(external_ref=None)), 422, "MISSING_FIELD", "external_ref")
        self._assert_error(self._post(self._payload(lines=[])), 422, "MISSING_FIELD", "lines")
        self._assert_error(
            self._post(self._payload(lines=[{"quantity": 1}])), 422, "MISSING_FIELD", "lines[0].default_code"
        )

    def test_invalid_json(self):
        self._assert_error(self._post(None, raw="{esto no es json"), 400, "INVALID_JSON", None)
        self._assert_error(self._post(["una", "lista"]), 400, "INVALID_JSON", None)

    def test_failed_call_creates_nothing(self):
        before = self.env["sale.order"].search_count([])
        lines = [{"default_code": "SHOP-001", "quantity": 1}, {"default_code": "NO-EXISTE", "quantity": 1}]
        self._post(self._payload(lines=lines))
        self.assertEqual(self.env["sale.order"].search_count([]), before)

    def test_duplicate_external_ref_is_409(self):
        self.assertEqual(self._post(self._payload()).status_code, 201)
        self._assert_error(self._post(self._payload()), 409, "DUPLICATE_EXTERNAL_REF", "external_ref")
        self.assertEqual(len(self._orders()), 1)

    def test_only_post(self):
        response = self.url_open(ORDERS_URL, headers=self._headers(self.api_key))
        self.assertEqual(response.status_code, 405)


class TestApiLog(ShopApiCase):
    """Tramo B: cada llamada queda registrada, también las que fallan, sin la API key."""

    def _logs(self):
        return self.env["shop.api.log"].search([], order="id")

    def test_every_call_is_logged(self):
        self.env["res.partner"].create({"name": "Cliente", "vat": "J-1"})
        self._get()                                                    # 200
        self._get({"updated_since": "ayer"})                           # 400
        self._get(key="clave-mala")                                    # 401
        self._post({"customer_vat": "J-1", "external_ref": "L-1",
                    "lines": [{"default_code": "SHOP-001", "quantity": 1}]})   # 201
        logs = self._logs()
        self.assertEqual(
            [(l.method, l.endpoint, l.status_code, l.error_code or False) for l in logs],
            [
                ("GET", "/api/v1/products", 200, False),
                ("GET", "/api/v1/products", 400, "INVALID_DATE"),
                ("GET", "/api/v1/products", 401, "INVALID_API_KEY"),
                ("POST", "/api/v1/orders", 201, False),
            ],
        )
        self.assertEqual(logs[0].user_id, self.api_user)
        self.assertFalse(logs[2].user_id, "Sin autenticar no hay usuario")
        self.assertTrue(all(l.duration_ms >= 0 for l in logs))
        self.assertEqual(logs[3].external_ref, "L-1")
        self.assertTrue(logs[3].order_id)

    def test_log_never_stores_the_key(self):
        self._get()
        self._get(key=self.api_key + "x")
        self._post({}, key=self.api_key)
        self.env.flush_all()
        self.env.cr.execute("SELECT row_to_json(l)::text FROM shop_api_log l")
        rows = [row[0] for row in self.env.cr.fetchall()]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertNotIn(self.api_key, row)
            self.assertNotIn(self.api_key[:8], row)

    def test_integration_user_cannot_read_logs(self):
        self.assertEqual(self._get().status_code, 200)
        with self.assertRaises(AccessError):
            self.env["shop.api.log"].with_user(self.api_user).search([])

    def test_each_call_runs_once(self):
        """Sin «retrying with a read/write cursor»: la petición no se ejecuta dos veces por escribir el log."""
        self.env["res.partner"].create({"name": "Cliente", "vat": "J-2"})
        with self.assertNoLogs("odoo.http", level="WARNING"), self.assertNoLogs("odoo.sql_db", level="ERROR"):
            self.assertEqual(self._get().status_code, 200)
            response = self._post({"customer_vat": "J-2", "external_ref": "ONCE-1",
                                   "lines": [{"default_code": "SHOP-001", "quantity": 1}]})
            self.assertEqual(response.status_code, 201, response.text)
