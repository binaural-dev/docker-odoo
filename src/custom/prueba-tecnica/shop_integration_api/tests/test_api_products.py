from datetime import datetime, timedelta

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestShopIntegrationApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Categorías de prueba
        cls.cat_tech = cls.env["product.category"].create({"name": "Tecnología"})
        cls.cat_home = cls.env["product.category"].create({"name": "Hogar"})

        # Productos de prueba
        cls.prod_tech_stock = cls.env["product.product"].create({
            "name": "Laptop Pro",
            "default_code": "LAP-01",
            "list_price": 1200.0,
            "categ_id": cls.cat_tech.id,
            "type": "product",
            "sale_ok": True,
            "active": True,
        })
        cls.prod_home_nostock = cls.env["product.product"].create({
            "name": "Cafetera Express",
            "default_code": "CAF-01",
            "list_price": 80.0,
            "categ_id": cls.cat_home.id,
            "type": "product",
            "sale_ok": True,
            "active": True,
        })
        cls.prod_unsaleable = cls.env["product.product"].create({
            "name": "Repuesto Interno",
            "default_code": "REP-01",
            "list_price": 25.0,
            "categ_id": cls.cat_tech.id,
            "sale_ok": False,
            "active": True,
        })
        cls.prod_archived = cls.env["product.product"].create({
            "name": "Monitor Obsoleto",
            "default_code": "MON-OLD",
            "list_price": 150.0,
            "categ_id": cls.cat_tech.id,
            "sale_ok": True,
            "active": False,
        })

        # Asignar stock disponible al producto Laptop Pro
        stock_location = cls.env["stock.location"].search([("usage", "=", "internal")], limit=1)
        if not stock_location:
            stock_location = cls.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if stock_location:
            cls.env["stock.quant"].create({
                "product_id": cls.prod_tech_stock.id,
                "location_id": stock_location.id,
                "quantity": 10.0,
            })

        # Usuario para autenticación de API con permisos de inventario para consultar stock
        cls.user_api = cls.env["res.users"].create({
            "name": "Shop API User",
            "login": "shop_api_user",
            "password": "shop_api_password_123",
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("stock.group_stock_user").id,
            ])],
        })

        # Commit para hacer visibles los registros al hilo HTTP de werkzeug
        cls.env.cr.commit()

    def test_unauthenticated_request_is_not_allowed(self):
        """Peticiones sin sesión activa deben ser rechazadas (redirección o no autorizado)."""
        response = self.url_open("/api/v1/products", allow_redirects=False)
        # En auth='user', Odoo redirige a login (302/303) o deniega (401/403)
        self.assertIn(
            response.status_code,
            [302, 303, 401, 403],
            "Petición anónima debe ser redirigida o rechazada.",
        )

    def test_get_all_products_authenticated(self):
        """Usuario autenticado obtiene solo productos activos y vendibles."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open("/api/v1/products")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        product_ids = [p["id"] for p in data]

        # Deben estar los productos vendibles y activos
        self.assertIn(self.prod_tech_stock.id, product_ids)
        self.assertIn(self.prod_home_nostock.id, product_ids)

        # No deben estar el no vendible ni el inactivo
        self.assertNotIn(self.prod_unsaleable.id, product_ids)
        self.assertNotIn(self.prod_archived.id, product_ids)

        # Validar estructura y datos del producto con stock
        item = next(p for p in data if p["id"] == self.prod_tech_stock.id)
        self.assertEqual(item["code"], "LAP-01")
        self.assertEqual(item["name"], "Laptop Pro")
        self.assertEqual(item["price"], 1200.0)
        self.assertEqual(item["qty_available"], 10.0)

    def test_filter_by_category(self):
        """Filtrar por category_id solo retorna productos de esa categoría."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open(f"/api/v1/products?category_id={self.cat_home.id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        product_ids = [p["id"] for p in data]
        self.assertIn(self.prod_home_nostock.id, product_ids)
        self.assertNotIn(self.prod_tech_stock.id, product_ids)

    def test_filter_by_invalid_category_returns_422(self):
        """Un category_id no entero debe responder 422 con JSON estructurado de error."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open("/api/v1/products?category_id=invalido")
        self.assertEqual(response.status_code, 422)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_FILTER")
        self.assertEqual(data["error"]["field"], "category_id")

    def test_filter_by_only_stock(self):
        """El parámetro only_stock=true solo retorna productos con stock disponible > 0."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open("/api/v1/products?only_stock=true")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        product_ids = [p["id"] for p in data]
        self.assertIn(self.prod_tech_stock.id, product_ids)
        self.assertNotIn(self.prod_home_nostock.id, product_ids)

    def test_filter_by_updated_since_valid(self):
        """Filtro de fecha updated_since con formato ISO válido."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        past_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        response = self.url_open(f"/api/v1/products?updated_since={past_date}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        product_ids = [p["id"] for p in data]
        self.assertIn(self.prod_tech_stock.id, product_ids)

    def test_filter_by_updated_since_invalid_format_returns_422(self):
        """Filtro de fecha updated_since con formato inválido debe retornar 422 (nunca 500)."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open("/api/v1/products?updated_since=fecha-invalida-31-12")
        self.assertEqual(response.status_code, 422)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_FILTER")
        self.assertEqual(data["error"]["field"], "updated_since")

    def test_filter_combined_category_and_stock(self):
        """Filtros combinados de categoría y stock."""
        self.authenticate(self.user_api.login, "shop_api_password_123")
        response = self.url_open(f"/api/v1/products?category_id={self.cat_tech.id}&only_stock=true")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        product_ids = [p["id"] for p in data]
        self.assertEqual(product_ids, [self.prod_tech_stock.id])

