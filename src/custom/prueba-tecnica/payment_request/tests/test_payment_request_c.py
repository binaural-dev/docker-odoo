from datetime import timedelta
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.sql_db import db_connect
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from .test_payment_request import TestPaymentRequestCommon


class TestPaymentCurrency(TestPaymentRequestCommon):
    """Tramo C: solicitud en USD pagada desde un diario en VES a la tasa de la fecha del pago."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.company.currency_id
        assert cls.usd.name == "USD", "Estas pruebas asumen una compañía en USD"
        cls.ves = cls.env.ref("base.VES")
        cls.ves.active = True
        cls.today = fields.Date.today()
        cls.yesterday = cls.today - timedelta(days=1)
        Rate = cls.env["res.currency.rate"]
        Rate.search([("currency_id", "=", cls.ves.id)]).unlink()
        # Tasa = bolívares por 1 USD (moneda de la compañía).
        Rate.create({"currency_id": cls.ves.id, "name": cls.yesterday, "rate": 30.0, "company_id": cls.env.company.id})
        Rate.create({"currency_id": cls.ves.id, "name": cls.today, "rate": 36.5, "company_id": cls.env.company.id})
        cls.ves_journal = cls.env["account.journal"].create({
            "name": "Banco en bolívares", "code": "BVES", "type": "bank", "currency_id": cls.ves.id,
        })

    def _pay_with(self, request, journal, date):
        wizard = self.env["payment.request.payment.wizard"].with_user(self.treasurer).create({
            "request_id": request.id, "journal_id": journal.id, "payment_date": date,
        })
        wizard.action_confirm()
        return request.payment_id

    def test_usd_request_paid_in_ves_at_payment_date_rate(self):
        # Solicitud del día anterior (tasa 30), pagada hoy (tasa 36,5): manda la fecha del pago.
        request = self._approved(amount=100.0, date=self.yesterday)
        payment = self._pay_with(request, self.ves_journal, self.today)
        self.assertEqual(request.state, "paid")
        self.assertEqual(payment.currency_id, self.ves)
        self.assertAlmostEqual(payment.amount, 3650.0)
        self.assertAlmostEqual(request.payment_rate, 36.5)
        self.assertEqual(request.payment_currency_id, self.ves)
        self.assertAlmostEqual(request.payment_amount, 3650.0)
        # En contabilidad: 3.650 Bs que valen 100 USD en la cuenta por pagar del proveedor.
        payable = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == "liability_payable")
        self.assertAlmostEqual(payable.amount_currency, 3650.0)
        self.assertAlmostEqual(payable.debit, 100.0)
        self.assertTrue(any("36.5" in body for body in request.message_ids.mapped("body")))

    def test_payment_on_other_date_uses_that_date_rate(self):
        request = self._approved(amount=100.0)
        payment = self._pay_with(request, self.ves_journal, self.yesterday)
        self.assertAlmostEqual(payment.amount, 3000.0)

    def test_same_currency_has_no_conversion(self):
        request = self._approved(amount=100.0)
        self._pay(request)
        self.assertAlmostEqual(request.payment_id.amount, 100.0)
        self.assertEqual(request.payment_rate, 1.0)

    def test_missing_rate_blocks_payment(self):
        request = self._approved(amount=100.0)
        tomorrow = self.today + timedelta(days=1)
        with self.assertRaises(UserError):
            self._pay_with(request, self.ves_journal, tomorrow)
        self.assertEqual(request.state, "approved")
        self.assertFalse(request.payment_id)

    def test_wizard_previews_converted_amount(self):
        request = self._approved(amount=100.0)
        wizard = self.env["payment.request.payment.wizard"].with_user(self.treasurer).create({
            "request_id": request.id, "journal_id": self.ves_journal.id, "payment_date": self.today,
        })
        self.assertEqual(wizard.payment_currency_id, self.ves)
        self.assertAlmostEqual(wizard.payment_amount, 3650.0)
        self.assertAlmostEqual(wizard.payment_rate, 36.5)
        wizard.payment_date = self.today + timedelta(days=1)
        self.assertIn("No hay tasa de VES", wizard.preview_warning)

    def test_report_shows_rate(self):
        request = self._approved(amount=100.0)
        self._pay_with(request, self.ves_journal, self.today)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "payment_request.action_report_payment_request", request.ids
        )[0].decode()
        self.assertIn("Tasa aplicada", html)
        self.assertIn("36.500000", html)


class TestPaymentAtomicity(TestPaymentRequestCommon):
    """Tramo C: si la creación del pago falla, la solicitud no queda en «pagada»."""

    def test_failed_payment_leaves_request_approved(self):
        request = self._approved()
        payment_model = type(self.env["account.payment"])
        with patch.object(payment_model, "action_post", side_effect=UserError("Banco no disponible")):
            with self.assertRaises(UserError) as caught:
                self._pay(request)
        self.assertIn("sigue aprobada", caught.exception.args[0])
        self.assertEqual(request.state, "approved")
        self.assertFalse(request.payment_id)
        self.assertFalse(self.env["account.payment"].search([("memo", "=", request.name)]))
        # Corregido el problema, se puede pagar normalmente.
        self._pay(request)
        self.assertEqual(request.state, "paid")


class TestPaymentMultiCompany(TestPaymentRequestCommon):
    """Tramo C: niveles y solicitudes por compañía, con reglas de registro."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Distribuidora Andina B", "currency_id": cls.company_a.currency_id.id})
        user_b_vals = {"company_id": cls.company_b.id, "company_ids": [(6, 0, cls.company_b.ids)]}
        cls.requester_b = new_test_user(cls.env, login="pr_requester_b", groups="base.group_user", **user_b_vals)
        cls.approver_b = new_test_user(
            cls.env, login="pr_approver_b", groups="base.group_user,payment_request.group_payment_request_approver",
            **user_b_vals,
        )
        cls.level_b = cls.env["payment.approval.level"].create({
            "company_id": cls.company_b.id, "min_amount": 0, "approver_id": cls.approver_b.id,
        })
        cls.request_a = cls.env["payment.request"].with_user(cls.requester).create({
            "partner_id": cls.vendor.id, "amount": 500.0, "concept": "Compañía A",
        })

    def test_user_of_b_sees_nothing_of_a(self):
        for user in (self.requester_b, self.approver_b):
            Request = self.env["payment.request"].with_user(user)
            self.assertNotIn(self.request_a, Request.search([]))
            with self.assertRaises(AccessError):
                self.request_a.with_user(user).read(["amount"])
        levels = self.env["payment.approval.level"].with_user(self.approver_b).search([])
        self.assertEqual(levels, self.level_b)
        self.assertNotIn(self.level_area, levels)

    def test_request_of_b_uses_levels_of_b(self):
        request_b = self.env["payment.request"].with_user(self.requester_b).create({
            "partner_id": self.vendor.id, "amount": 500.0, "concept": "Compañía B",
        })
        self.assertEqual(request_b.company_id, self.company_b)
        request_b.action_submit()
        self.assertEqual(request_b.approver_id, self.approver_b)  # no el aprobador de la compañía A
        request_b.with_user(self.approver_b).action_approve()
        self.assertEqual(request_b.state, "approved")

    def test_level_approver_must_belong_to_company(self):
        with self.assertRaises(ValidationError):
            self.env["payment.approval.level"].create({
                "company_id": self.company_b.id, "min_amount": 1000, "approver_id": self.approver.id,
            })

    def test_cannot_pay_from_journal_of_other_company(self):
        request = self._approved()
        journal_b = self.env["account.journal"].create({
            "name": "Banco B", "code": "BNKB", "type": "bank", "company_id": self.company_b.id,
        })
        with self.assertRaises(UserError):
            self._as(request, self.treasurer)._create_payment(journal_b, fields.Date.today())


@tagged("post_install", "-at_install")
class TestPaymentRequestConcurrency(TransactionCase):
    """Tramo C: dos personas actúan a la vez sobre la misma solicitud; solo una gana.

    Usa dos conexiones REALES a la base, cada una con su transacción, porque es la única forma de probar un
    bloqueo. Por eso los datos se confirman (commit) y se borran al terminar.
    """

    def _connect(self, uid=SUPERUSER_ID):
        cr = db_connect(self.env.cr.dbname).cursor()
        self.addCleanup(cr.close)
        return api.Environment(cr, uid, {})

    def _setup_committed_request(self, tag):
        env = self._connect()
        approver_groups = "base.group_user,payment_request.group_payment_request_approver"
        treasury_groups = "base.group_user,payment_request.group_payment_request_treasury"
        users = {
            "requester": new_test_user(env, login=f"conc_req_{tag}", groups="base.group_user"),
            "approver": new_test_user(env, login=f"conc_app_{tag}", groups=approver_groups),
            "treasurer_1": new_test_user(env, login=f"conc_tr1_{tag}", groups=treasury_groups),
            "treasurer_2": new_test_user(env, login=f"conc_tr2_{tag}", groups=treasury_groups),
        }
        level = env["payment.approval.level"].create({"min_amount": 0.5, "approver_id": users["approver"].id})
        partner = env["res.partner"].create({"name": f"Proveedor concurrencia {tag}"})
        request = env["payment.request"].with_user(users["requester"]).create({
            "partner_id": partner.id, "amount": 150.0, "concept": "Prueba de concurrencia",
        })
        request.action_submit()
        env.cr.commit()
        self.addCleanup(self._cleanup, request.id, level.id, partner.id, [u.id for u in users.values()])
        return request.id, users

    def _cleanup(self, request_id, level_id, partner_id, user_ids):
        env = self._connect()
        request = env["payment.request"].browse(request_id)
        if request.payment_id:
            request.payment_id.action_draft()
            request.payment_id.unlink()
        env.cr.execute("DELETE FROM payment_request WHERE id = %s", [request_id])
        env["payment.approval.level"].browse(level_id).unlink()
        env["res.users"].browse(user_ids).write({"active": False})
        env["res.partner"].browse(partner_id).write({"active": False})
        env.cr.commit()

    def _state(self, request_id):
        env = self._connect()
        return env["payment.request"].browse(request_id).state

    def test_approve_and_reject_at_the_same_time(self):
        request_id, users = self._setup_committed_request("ar")
        env_a = self._connect(users["approver"].id)  # pestaña 1: aprueba
        env_b = self._connect(users["approver"].id)  # pestaña 2: rechaza al mismo tiempo
        env_a["payment.request"].browse(request_id).action_approve()  # toma el bloqueo, sin confirmar aún

        with self.assertRaises(UserError) as caught:
            env_b["payment.request"].browse(request_id).action_reject("Rechazo simultáneo")
        self.assertIn("Otra persona está procesando", caught.exception.args[0])
        env_b.cr.rollback()

        env_a.cr.commit()  # la primera termina
        env_b.invalidate_all()
        with self.assertRaises(UserError):  # ahora la segunda ve «aprobada»: la transición ya no vale
            env_b["payment.request"].browse(request_id).action_reject("Rechazo tardío")
        env_b.cr.rollback()
        self.assertEqual(self._state(request_id), "approved")

    def test_two_treasurers_pay_at_the_same_time(self):
        request_id, users = self._setup_committed_request("pay")
        env = self._connect(users["approver"].id)
        env["payment.request"].browse(request_id).action_approve()
        env.cr.commit()
        journal = self._connect()["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)], limit=1
        )
        env_a = self._connect(users["treasurer_1"].id)
        env_b = self._connect(users["treasurer_2"].id)
        today = fields.Date.today()
        env_a["payment.request"].browse(request_id)._create_payment(env_a["account.journal"].browse(journal.id), today)

        with self.assertRaises(UserError):
            env_b["payment.request"].browse(request_id)._create_payment(env_b["account.journal"].browse(journal.id), today)
        env_b.cr.rollback()
        env_a.cr.commit()

        check = self._connect()
        request = check["payment.request"].browse(request_id)
        self.assertEqual(request.state, "paid")
        self.assertEqual(check["account.payment"].search_count([("memo", "=", request.name)]), 1)
