from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestPaymentRequestCommon(TransactionCase):
    """Las pruebas corren con usuarios reales de cada grupo, no como administrador."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # base.group_user implica Solicitante: cualquier empleado puede pedir pagos.
        cls.requester = new_test_user(cls.env, login="pr_requester", groups="base.group_user", name="Empleado")
        cls.other_requester = new_test_user(cls.env, login="pr_other", groups="base.group_user", name="Otro empleado")
        approver_groups = "base.group_user,payment_request.group_payment_request_approver"
        cls.approver = new_test_user(cls.env, login="pr_approver", groups=approver_groups, name="Jefe de área")
        cls.manager = new_test_user(cls.env, login="pr_manager", groups=approver_groups, name="Gerente general")
        cls.treasurer = new_test_user(
            cls.env, login="pr_treasurer", name="Tesorero",
            groups="base.group_user,payment_request.group_payment_request_treasury",
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor de prueba", "vat": "J-12345678-9"})
        # Niveles: hasta 4.999,99 el jefe del área; desde 5.000 gerencia.
        cls.env["payment.approval.level"].search([]).unlink()
        cls.level_area = cls.env["payment.approval.level"].create({"min_amount": 0, "approver_id": cls.approver.id})
        cls.level_mgmt = cls.env["payment.approval.level"].create({"min_amount": 5000, "approver_id": cls.manager.id})
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)], limit=1
        )

    def _new_request(self, user=None, **vals):
        values = {"partner_id": self.vendor.id, "amount": 150.0, "concept": "Mantenimiento del aire acondicionado"}
        values.update(vals)
        return self.env["payment.request"].with_user(user or self.requester).create(values)

    def _as(self, request, user):
        return request.with_user(user)

    def _submitted(self, **vals):
        request = self._new_request(**vals)
        request.action_submit()
        return request

    def _approved(self, **vals):
        request = self._submitted(**vals)
        self._as(request, request.approver_id).action_approve()
        return request

    def _pay(self, request, user=None):
        wizard = self.env["payment.request.payment.wizard"].with_user(user or self.treasurer).create({
            "request_id": request.id, "journal_id": self.bank_journal.id,
        })
        return wizard.action_confirm()


class TestPaymentRequestFlow(TestPaymentRequestCommon):
    """Tramo A: flujo, visibilidad y lo que cada rol no puede hacer."""

    def test_defaults_and_sequence(self):
        request = self._new_request()
        self.assertRegex(request.name, r"^SP/%d/\d{4}$" % fields.Date.today().year)
        self.assertEqual(request.requester_id, self.requester)
        self.assertEqual(request.currency_id, self.env.company.currency_id)
        self.assertEqual(request.state, "draft")
        self.assertNotEqual(self._new_request().name, request.name)

    def test_full_flow_paid(self):
        request = self._new_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        self._as(request, self.approver).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approved_by_id, self.approver)
        self.assertTrue(request.approval_date)
        self._pay(request)
        self.assertEqual(request.state, "paid")

    def test_state_changes_are_tracked_in_chatter(self):
        request = self._new_request()
        # El seguimiento del chatter se publica al cerrar la transacción (precommit).
        self.env.cr.precommit.run()
        request.action_submit()
        self.env.cr.precommit.run()
        # sudo() solo para leer el resultado: mail.tracking.value no es legible por un empleado.
        tracked = request.sudo().message_ids.tracking_value_ids.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(tracked)

    def test_requester_sees_only_own(self):
        own = self._new_request()
        other = self._new_request(user=self.other_requester)
        visible = self.env["payment.request"].with_user(self.requester).search([])
        self.assertIn(own, visible)
        self.assertNotIn(other, visible)
        with self.assertRaises(AccessError):
            other.with_user(self.requester).read(["amount"])

    def test_approver_and_treasury_see_all(self):
        own = self._new_request()
        other = self._new_request(user=self.other_requester)
        for user in (self.approver, self.treasurer):
            visible = self.env["payment.request"].with_user(user).search([])
            self.assertIn(own, visible)
            self.assertIn(other, visible)

    def test_requester_cannot_approve_by_method(self):
        request = self._submitted()
        with self.assertRaises(AccessError):
            request.action_approve()
        with self.assertRaises(AccessError):
            request.action_reject("No me gusta")
        self.assertEqual(request.state, "submitted")

    def test_flow_fields_cannot_be_written_directly(self):
        """Un write directo (por ejemplo por RPC) no salta el flujo, ni siquiera para el aprobador o tesorería."""
        request = self._submitted()
        for user, vals in [
            (self.requester, {"state": "approved"}),
            (self.requester, {"approver_id": self.requester.id}),
            (self.approver, {"state": "approved", "approved_by_id": self.manager.id}),
            (self.treasurer, {"state": "paid"}),
        ]:
            with self.assertRaises(AccessError):
                self._as(request, user).write(vals)
        self.assertEqual(request.state, "submitted")
        self.assertEqual(request.approver_id, self.approver)

    def test_requester_cannot_pay(self):
        request = self._approved()
        with self.assertRaises(AccessError):
            self._pay(request, user=self.requester)
        with self.assertRaises(AccessError):
            request._create_payment(self.bank_journal, fields.Date.today())

    def test_requester_cannot_create_in_other_state(self):
        with self.assertRaises(UserError):
            self._new_request(state="approved")
        with self.assertRaises(UserError):
            self._new_request(approver_id=self.requester.id)

    def test_submitted_request_is_locked(self):
        request = self._submitted()
        for user in (self.requester, self.approver):
            with self.assertRaises(UserError):
                self._as(request, user).write({"amount": 9999.0})
            with self.assertRaises(UserError):
                self._as(request, user).write({"partner_id": self.env["res.partner"].create({"name": "Otro"}).id})
        with self.assertRaises(UserError):
            request.unlink()
        self.assertEqual(request.amount, 150.0)

    def test_draft_request_is_editable_and_deletable(self):
        request = self._new_request()
        request.write({"amount": 200.0, "concept": "Otro concepto"})
        self.assertEqual(request.amount, 200.0)
        request.unlink()
        self.assertFalse(request.exists())

    def test_amount_must_be_positive(self):
        for amount in (0.0, -10.0):
            with self.assertRaises(ValidationError):
                self._new_request(amount=amount)
        request = self._new_request()
        with self.assertRaises(ValidationError):
            request.write({"amount": 0.0})

    def test_approver_cannot_approve_own_request(self):
        # El jefe del área pide 6.000: le toca a gerencia, y él no puede aprobarla.
        request = self._new_request(user=self.approver, amount=6000.0)
        request.action_submit()
        self.assertEqual(request.approver_id, self.manager)
        with self.assertRaises(UserError):
            request.action_approve()
        # Si el nivel le asigna su propia solicitud, no se puede enviar.
        own = self._new_request(user=self.approver)
        with self.assertRaises(UserError):
            own.action_submit()

    def test_invalid_transitions(self):
        request = self._new_request()
        with self.assertRaises(UserError):
            self._as(request, self.treasurer)._create_payment(self.bank_journal, fields.Date.today())  # sin aprobar
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()  # dos veces
        with self.assertRaises(AccessError):
            self._as(request, self.treasurer).action_approve()  # tesorería no aprueba
        self._as(request, self.approver).action_reject("Falta la factura")
        with self.assertRaises(UserError):
            self._as(request, self.approver).action_approve()  # rechazada es final

    def _form_buttons(self, user):
        arch = self.env["payment.request"].with_user(user).get_views([(False, "form")])["views"]["form"]["arch"]
        return {b.get("name"): b.get("invisible") for b in etree.fromstring(arch).iter("button")}

    def test_buttons_by_group_and_state(self):
        requester_buttons = self._form_buttons(self.requester)
        self.assertEqual(requester_buttons["action_submit"], "state != 'draft'")
        self.assertNotIn("action_approve", requester_buttons)
        self.assertNotIn("action_open_reject_wizard", requester_buttons)
        self.assertNotIn("action_open_payment_wizard", requester_buttons)

        approver_buttons = self._form_buttons(self.approver)
        self.assertEqual(approver_buttons["action_approve"], "state != 'submitted' or approver_id != uid")
        self.assertEqual(approver_buttons["action_open_reject_wizard"], "state != 'submitted' or approver_id != uid")
        self.assertNotIn("action_open_payment_wizard", approver_buttons)

        treasury_buttons = self._form_buttons(self.treasurer)
        self.assertEqual(treasury_buttons["action_open_payment_wizard"], "state != 'approved'")
        self.assertNotIn("action_approve", treasury_buttons)


class TestPaymentRequestApprovalLevels(TestPaymentRequestCommon):
    """Tramo B: niveles de aprobación, actividad y aprobador asignado."""

    def test_level_assigned_by_amount(self):
        cases = [(150.0, self.approver), (4999.99, self.approver), (5000.0, self.manager), (80000.0, self.manager)]
        for amount, expected in cases:
            request = self._submitted(amount=amount)
            self.assertEqual(request.approver_id, expected, amount)

    def test_level_uses_company_currency(self):
        """El umbral está en la moneda de la compañía: 3.000 en otra moneda a tasa 0,5 son 6.000 -> gerencia."""
        other = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", self.env.company.currency_id.id)], limit=1
        )
        other.active = True
        self.env["res.currency.rate"].create({
            "currency_id": other.id, "rate": 0.5, "name": fields.Date.today(), "company_id": self.env.company.id,
        })
        request = self._submitted(amount=3000.0, currency_id=other.id)
        self.assertEqual(request.approver_id, self.manager)

    def test_activity_for_assigned_approver(self):
        request = self._submitted()
        activity = request.activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.approver)
        self._as(request, self.approver).action_approve()
        self.assertFalse(request.activity_ids, "La actividad se cierra al aprobar")

    def test_no_level_blocks_submit(self):
        self.env["payment.approval.level"].search([]).unlink()
        request = self._new_request()
        with self.assertRaises(UserError):
            request.action_submit()
        self.assertEqual(request.state, "draft")

    def test_only_assigned_approver_can_approve(self):
        small = self._submitted()  # le toca al jefe del área
        with self.assertRaises(AccessError):
            self._as(small, self.manager).action_approve()
        big = self._submitted(amount=7000.0)  # le toca a gerencia
        with self.assertRaises(AccessError):
            self._as(big, self.approver).action_approve()
        with self.assertRaises(AccessError):
            self._as(big, self.approver).action_reject("No")
        self._as(big, self.manager).action_approve()
        self.assertEqual(big.approved_by_id, self.manager)

    def test_level_approver_must_be_approver(self):
        with self.assertRaises(ValidationError):
            self.env["payment.approval.level"].create({"min_amount": 100, "approver_id": self.requester.id})

    def test_requester_cannot_configure_levels(self):
        with self.assertRaises(AccessError):
            self.env["payment.approval.level"].with_user(self.requester).create(
                {"min_amount": 1, "approver_id": self.approver.id}
            )
        with self.assertRaises(AccessError):
            self.level_area.with_user(self.approver).write({"min_amount": 1})


class TestPaymentRequestRejectAndPay(TestPaymentRequestCommon):
    """Tramo B: wizard de rechazo, wizard de pago y reporte."""

    def test_reject_wizard_reason_in_chatter(self):
        request = self._submitted()
        form = Form(self.env["payment.request.reject.wizard"].with_user(self.approver).with_context(
            default_request_id=request.id))
        form.reason = "Falta la factura del proveedor"
        form.save().action_confirm()
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.rejection_reason, "Falta la factura del proveedor")
        bodies = request.message_ids.mapped("body")
        self.assertTrue(any("Falta la factura del proveedor" in body for body in bodies))
        self.assertFalse(request.activity_ids, "La actividad se cierra al rechazar")

    def test_reject_requires_reason(self):
        request = self._submitted()
        for reason in ("", "   ", None):
            with self.assertRaises(UserError):
                self._as(request, self.approver).action_reject(reason)
        self.assertEqual(request.state, "submitted")

    def test_payment_wizard_creates_linked_vendor_payment(self):
        self.assertTrue(self.bank_journal, "La base de pruebas necesita un diario de banco")
        request = self._approved()
        self._pay(request)
        payment = request.payment_id
        self.assertEqual(request.state, "paid")
        self.assertTrue(payment)
        self.assertEqual(payment.payment_type, "outbound")
        self.assertEqual(payment.partner_type, "supplier")
        self.assertEqual(payment.partner_id, self.vendor)
        self.assertEqual(payment.amount, 150.0)
        self.assertEqual(payment.journal_id, self.bank_journal)
        self.assertEqual(payment.memo, request.name)
        self.assertNotEqual(payment.state, "draft")
        # Registrado en contabilidad: asiento publicado contra la cuenta por pagar del proveedor.
        self.assertTrue(payment.move_id, "El pago debe generar su asiento contable")
        self.assertEqual(payment.move_id.state, "posted")
        payable = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        self.assertEqual(payable.partner_id, self.vendor)
        self.assertAlmostEqual(payable.debit, 150.0)
        # Visible desde la solicitud: botón inteligente al pago.
        action = request.with_user(self.treasurer).action_view_payment()
        self.assertEqual(action["res_id"], payment.id)

    def test_cannot_pay_twice(self):
        request = self._approved()
        self._pay(request)
        with self.assertRaises(UserError):
            self._pay(request)
        with self.assertRaises(UserError):
            self._as(request, self.treasurer)._create_payment(self.bank_journal, fields.Date.today())
        payments = self.env["account.payment"].search([("memo", "=", request.name)])
        self.assertEqual(len(payments), 1)

    def test_approver_cannot_pay(self):
        request = self._approved()
        with self.assertRaises(AccessError):
            self._pay(request, user=self.approver)

    def test_report_shows_who_approved_and_when(self):
        request = self._approved()
        html, _format = self.env["ir.actions.report"]._render_qweb_html(
            "payment_request.action_report_payment_request", request.ids
        )
        html = html.decode()
        self.assertIn(request.name, html)
        self.assertIn("Proveedor de prueba", html)
        self.assertIn("Aprobada por", html)
        self.assertIn("Jefe de área", html)
        self.assertIn("Fecha de aprobación", html)
        self.assertIn(str(request.approval_date.year), html)

    def test_report_rejected_shows_reason(self):
        request = self._submitted()
        self._as(request, self.approver).action_reject("Monto duplicado")
        html = self.env["ir.actions.report"]._render_qweb_html(
            "payment_request.action_report_payment_request", request.ids
        )[0].decode()
        self.assertIn("Monto duplicado", html)
