from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    """Las pruebas corren con usuarios reales de cada grupo, no como administrador."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # base.group_user implica Solicitante: cualquier empleado puede pedir pagos.
        cls.requester = new_test_user(cls.env, login="pr_requester", groups="base.group_user", name="Empleado")
        cls.other_requester = new_test_user(cls.env, login="pr_other", groups="base.group_user", name="Otro empleado")
        cls.approver = new_test_user(
            cls.env, login="pr_approver", name="Jefe de área",
            groups="base.group_user,payment_request.group_payment_request_approver",
        )
        cls.treasurer = new_test_user(
            cls.env, login="pr_treasurer", name="Tesorero",
            groups="base.group_user,payment_request.group_payment_request_treasury",
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor de prueba"})

    def _new_request(self, user=None, **vals):
        values = {"partner_id": self.vendor.id, "amount": 150.0, "concept": "Mantenimiento del aire acondicionado"}
        values.update(vals)
        return self.env["payment.request"].with_user(user or self.requester).create(values)

    def _as(self, request, user):
        return request.with_user(user)

    # Flujo

    def test_defaults_and_sequence(self):
        request = self._new_request()
        self.assertRegex(request.name, r"^SP/%d/\d{4}$" % fields.Date.today().year)
        self.assertEqual(request.requester_id, self.requester)
        self.assertEqual(request.currency_id, self.env.company.currency_id)
        self.assertEqual(request.state, "draft")
        second = self._new_request()
        self.assertNotEqual(second.name, request.name)

    def test_full_flow_paid(self):
        request = self._new_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        self._as(request, self.approver).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approved_by_id, self.approver)
        self.assertTrue(request.approval_date)
        self._as(request, self.treasurer).action_mark_paid()
        self.assertEqual(request.state, "paid")

    def test_reject_flow(self):
        request = self._new_request()
        request.action_submit()
        self._as(request, self.approver).action_reject()
        self.assertEqual(request.state, "rejected")
        self.assertFalse(request.approved_by_id)

    def test_state_changes_are_tracked_in_chatter(self):
        request = self._new_request()
        # El seguimiento del chatter se publica al cerrar la transacción (precommit).
        self.env.cr.precommit.run()
        request.action_submit()
        self.env.cr.precommit.run()
        # sudo() solo para leer el resultado: mail.tracking.value no es legible por un empleado.
        tracked = request.sudo().message_ids.tracking_value_ids.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(tracked)

    # Lo que el solicitante NO puede hacer

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
        request = self._new_request()
        request.action_submit()
        with self.assertRaises(AccessError):
            request.action_approve()
        with self.assertRaises(AccessError):
            request.action_reject()
        self.assertEqual(request.state, "submitted")

    def test_requester_cannot_approve_by_write(self):
        """Un write directo (por ejemplo por RPC) tampoco salta el control."""
        request = self._new_request()
        request.action_submit()
        with self.assertRaises(AccessError):
            request.write({"state": "approved"})
        with self.assertRaises(UserError):
            request.write({"approved_by_id": self.requester.id})
        self.assertEqual(request.state, "submitted")

    def test_requester_cannot_mark_paid(self):
        request = self._new_request()
        request.action_submit()
        self._as(request, self.approver).action_approve()
        with self.assertRaises(AccessError):
            request.action_mark_paid()

    def test_requester_cannot_create_in_other_state(self):
        with self.assertRaises(UserError):
            self._new_request(state="approved")

    def test_submitted_request_is_locked(self):
        request = self._new_request()
        request.action_submit()
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

    # Reglas de negocio

    def test_amount_must_be_positive(self):
        for amount in (0.0, -10.0):
            with self.assertRaises(ValidationError):
                self._new_request(amount=amount)
        request = self._new_request()
        with self.assertRaises(ValidationError):
            request.write({"amount": 0.0})

    def test_approver_cannot_approve_own_request(self):
        request = self._new_request(user=self.approver)
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_approve()

    def test_invalid_transitions(self):
        request = self._new_request()
        with self.assertRaises(UserError):
            self._as(request, self.approver).action_approve()  # en borrador, sin enviar
        with self.assertRaises(UserError):
            self._as(request, self.treasurer).action_mark_paid()  # sin aprobar
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()  # dos veces
        with self.assertRaises(AccessError):
            self._as(request, self.treasurer).action_approve()  # tesorería no aprueba
        self._as(request, self.approver).action_reject()
        with self.assertRaises(UserError):
            self._as(request, self.approver).action_approve()  # rechazada es final

    # Botones: estado y grupo

    def _form_buttons(self, user):
        arch = self.env["payment.request"].with_user(user).get_views([(False, "form")])["views"]["form"]["arch"]
        return {b.get("name"): b.get("invisible") for b in etree.fromstring(arch).iter("button")}

    def test_buttons_by_group_and_state(self):
        requester_buttons = self._form_buttons(self.requester)
        self.assertEqual(requester_buttons, {"action_submit": "state != 'draft'"})

        approver_buttons = self._form_buttons(self.approver)
        self.assertEqual(approver_buttons["action_approve"], "state != 'submitted'")
        self.assertEqual(approver_buttons["action_reject"], "state != 'submitted'")
        self.assertNotIn("action_mark_paid", approver_buttons)

        treasury_buttons = self._form_buttons(self.treasurer)
        self.assertEqual(treasury_buttons["action_mark_paid"], "state != 'approved'")
        self.assertNotIn("action_approve", treasury_buttons)
