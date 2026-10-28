import json

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

URL = "/api/v1/products"


@tagged("post_install", "-at_install")
class TestProductsApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Usuario dedicado a la integración, con los permisos mínimos para ver productos y stock.
        # new_test_user usa el login como contraseña.
        cls.api_user = new_test_user(
            cls.env, login="shop_api_user", name="Tienda en línea",
            groups="base.group_user,sales_team.group_sale_salesman,stock.group_stock_user",
        )
        cls.no_stock_user = new_test_user(cls.env, login="shop_api_nostock", groups="base.group_user")
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
    def _product(cls, code, name, categ, price, qty=0, sale_ok=True):
        product = cls.env["product.product"].create({
            "name": name, "default_code": code, "categ_id": categ.id, "list_price": price,
            "is_storable": True, "sale_ok": sale_ok,
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

    def _get(self, params=None, authenticate=True):
        if authenticate:
            self.authenticate("shop_api_user", "shop_api_user")
        query = "&".join(f"{key}={value}" for key, value in (params or {}).items())
        return self.url_open(f"{URL}?{query}" if query else URL, allow_redirects=False)

    def _ids(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return {item["id"] for item in response.json()["data"]}

    # Respuesta y productos visibles

    def test_response_fields(self):
        body = self._get({"category_id": self.categ_shop.id}).json()
        self.assertEqual(body["currency"], self.env.company.currency_id.name)
        item = next(i for i in body["data"] if i["id"] == self.p_stock.id)
        self.assertEqual(item, {
            "id": self.p_stock.id, "default_code": "SHOP-001", "name": "Mouse", "price": 25.0, "available_qty": 10.0,
        })
        self.assertEqual(body["count"], len(body["data"]))

    def test_only_active_and_sellable(self):
        ids = self._get().json()["data"]
        ids = {item["id"] for item in ids}
        self.assertTrue({self.p_stock.id, self.p_no_stock.id, self.p_other.id} <= ids)
        self.assertNotIn(self.p_not_sellable.id, ids)
        self.assertNotIn(self.p_archived.id, ids)

    # Filtros solos

    def test_filter_category_includes_children(self):
        ids = self._ids(self._get({"category_id": self.categ_shop.id}))
        self.assertEqual(ids, {self.p_stock.id, self.p_no_stock.id})

    def test_filter_in_stock(self):
        ids = self._ids(self._get({"in_stock": "true"}))
        self.assertIn(self.p_stock.id, ids)
        self.assertIn(self.p_other.id, ids)
        self.assertNotIn(self.p_no_stock.id, ids)
        all_ids = self._ids(self._get({"in_stock": "false"}))
        self.assertIn(self.p_no_stock.id, all_ids)

    def test_filter_updated_since(self):
        ids = self._ids(self._get({"updated_since": "2024-01-01"}))
        self.assertIn(self.p_stock.id, ids)
        self.assertNotIn(self.p_other.id, ids)
        ids = self._ids(self._get({"updated_since": "2019-12-31T23:00:00Z"}))
        self.assertIn(self.p_other.id, ids)
        # Con zona horaria: 2020-01-01 00:00 UTC son las 20:00 del 31/12 en Venezuela (-04:00).
        self.assertIn(self.p_other.id, self._ids(self._get({"updated_since": "2019-12-31T20:00:00-04:00"})))
        self.assertNotIn(self.p_other.id, self._ids(self._get({"updated_since": "2019-12-31T20:00:01-04:00"})))

    def test_updated_since_sees_template_changes(self):
        """Cambiar el precio (campo de la plantilla) cuenta como modificación del producto."""
        self.p_other.product_tmpl_id.list_price = 85.0
        self.env.flush_all()
        ids = self._ids(self._get({"updated_since": "2024-01-01"}))
        self.assertIn(self.p_other.id, ids)

    # Filtros combinados

    def test_filters_combined(self):
        ids = self._ids(self._get({"category_id": self.categ_shop.id, "in_stock": "1"}))
        self.assertEqual(ids, {self.p_stock.id})
        ids = self._ids(self._get({"category_id": self.categ_other.id, "in_stock": "1", "updated_since": "2024-01-01"}))
        self.assertEqual(ids, set())
        ids = self._ids(self._get({"category_id": self.categ_other.id, "in_stock": "1", "updated_since": "2019-01-01"}))
        self.assertEqual(ids, {self.p_other.id})

    # Errores: claros y nunca un 500

    def _assert_error(self, response, status, code, field):
        self.assertEqual(response.status_code, status, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        self.assertEqual(error["field"], field)
        self.assertTrue(error["message"])
        return error

    def test_invalid_date(self):
        for value in ("27/10/2026", "2026-13-01", "ayer", "2026-10-27T25:00:00"):
            error = self._assert_error(self._get({"updated_since": value}), 400, "INVALID_DATE", "updated_since")
            self.assertIn(value, error["message"])

    def test_invalid_category(self):
        self._assert_error(self._get({"category_id": "abc"}), 400, "INVALID_PARAMETER", "category_id")
        self._assert_error(self._get({"category_id": "999999"}), 422, "CATEGORY_NOT_FOUND", "category_id")

    def test_invalid_in_stock(self):
        self._assert_error(self._get({"in_stock": "quizas"}), 400, "INVALID_PARAMETER", "in_stock")

    def test_requires_login(self):
        response = self._get(authenticate=False)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn("/web/login", response.headers.get("Location", ""))

    def test_user_without_stock_rights(self):
        """Sin permisos de inventario: 403 claro con el formato de la API, no un error genérico."""
        self.authenticate("shop_api_nostock", "shop_api_nostock")
        response = self.url_open(URL, allow_redirects=False)
        self._assert_error(response, 403, "FORBIDDEN", None)

    def test_only_get(self):
        self.authenticate("shop_api_user", "shop_api_user")
        response = self.url_open(URL, data={"x": "1"})
        self.assertEqual(response.status_code, 405)

    def test_response_is_json(self):
        response = self._get()
        self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
        json.loads(response.text)
