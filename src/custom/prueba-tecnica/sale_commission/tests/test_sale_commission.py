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
        cls.other_salesman = new_test_user(
            cls.env, login="commission_other_salesman", groups="sales_team.group_sale_salesman",
            name="Otro vendedor",
        )
        cls.other_salesman.commission_percent = 3.0
        cls.partner = cls.env["res.partner"].create({"name": "Cliente de prueba"})
        cls.product = cls.env["product.product"].create({
            "name": "Producto de prueba",
            "list_price": 100.0,
            "taxes_id": [(5, 0, 0)],
        })

    def _create_order(self, user, qty=2):
        return self.env["sale.order"].with_user(user).create({
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
