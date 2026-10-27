from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestSaleCommission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesman = new_test_user(
            cls.env, login="commission_salesman", groups="sales_team.group_sale_salesman",
            name="Vendedor de prueba",
        )
        cls.salesman.commission_percent = 5.0
        cls.env.user.commission_percent = 5.0
        cls.other_salesman = new_test_user(
            cls.env, login="commission_other_salesman", groups="sales_team.group_sale_salesman",
            name="Otro vendedor",
        )
        cls.other_salesman.commission_percent = 3.0
        cls.partner = cls.env["res.partner"].create({"name": "Cliente de prueba"})
        cls.category = cls.env["product.category"].create({"name": "Repuestos"})
        cls.product = cls.env["product.product"].create({
            "name": "Producto de prueba",
            "categ_id": cls.category.id,
            "list_price": 100.0,
            "taxes_id": [(5, 0, 0)],
        })

    def _create_order(self, user, qty=2):
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "user_id": user.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty})],
        })

    def test_commission_on_confirm(self):
        order = self._create_order(self.salesman)
        self.assertEqual(order.order_line.commission_amount, 0.0)
        order.action_confirm()
        self.assertEqual(order.order_line.commission_percent, 5.0)
        self.assertAlmostEqual(order.order_line.commission_amount, 10.0)

    def test_salesman_report_only_own(self):
        self._create_order(self.salesman).action_confirm()
        self._create_order(self.other_salesman).action_confirm()
        self.env.flush_all()
        lines = self.env["sale.commission.report"].with_user(self.salesman).search([])
        self.assertTrue(lines)
        self.assertEqual(lines.mapped("user_id"), self.salesman)

    def test_commission_by_category(self):
        self.category.commission_percent = 8.0
        order = self._create_order(self.salesman)
        order.action_confirm()
        self.assertEqual(order.order_line.commission_percent, 8.0)
        self.assertAlmostEqual(order.order_line.commission_amount, 16.0)

    def test_subcategory_uses_most_specific_rule(self):
        self.category.commission_percent = 8.0
        child = self.env["product.category"].create({"name": "Frenos", "parent_id": self.category.id})
        child.commission_percent = 10.0
        self.product.categ_id = child
        order = self._create_order(self.salesman)
        order.action_confirm()
        self.assertEqual(order.order_line.commission_percent, 10.0)

    # T-200: los vendedores no podían confirmar pedidos (AccessError sobre sale.commission.rule).
    # Estas pruebas corren con el usuario vendedor, no como administrador.

    def _create_order_as(self, user, qty=2):
        return self.env["sale.order"].with_user(user).create({
            "partner_id": self.partner.id,
            "user_id": user.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty})],
        })

    def test_t200_salesman_confirms_own_order(self):
        order = self._create_order_as(self.salesman)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.order_line.commission_percent, 5.0)

    def test_t200_salesman_confirm_uses_category_rule(self):
        self.category.commission_percent = 8.0
        order = self._create_order_as(self.salesman)
        order.action_confirm()
        self.assertEqual(order.order_line.commission_percent, 8.0)

    def test_t200_manager_still_confirms(self):
        manager = new_test_user(
            self.env, login="commission_manager", groups="sales_team.group_sale_manager",
            name="Gerente de prueba",
        )
        order = self._create_order(self.salesman).with_user(manager)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_t200_salesman_cannot_manage_rules(self):
        self.category.commission_percent = 8.0
        rule = self.category.commission_rule_ids.with_user(self.salesman)
        with self.assertRaises(AccessError):
            rule.percent = 50.0
        with self.assertRaises(AccessError):
            self.env["sale.commission.rule"].with_user(self.salesman).create({
                "categ_id": self.category.id, "percent": 50.0,
            })
        with self.assertRaises(AccessError):
            rule.unlink()
