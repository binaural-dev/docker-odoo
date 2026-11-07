from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env["res.partner"].create({
            "name": "Proveedor Andino S.A.",
            "supplier_rank": 1,
        })
        
        # Grupo Solicitante
        group_user = cls.env.ref("payment_request.group_payment_request_user")
        # Grupo Aprobador
        group_approver = cls.env.ref("payment_request.group_payment_request_approver")
        # Grupo Tesorería
        group_treasury = cls.env.ref("payment_request.group_payment_request_treasury")

        cls.user_applicant = cls.env["res.users"].create({
            "name": "Empleado Solicitante",
            "login": "applicant_test",
            "groups_id": [(6, 0, [group_user.id])],
        })
        cls.user_other_applicant = cls.env["res.users"].create({
            "name": "Otro Empleado",
            "login": "other_applicant_test",
            "groups_id": [(6, 0, [group_user.id])],
        })
        cls.user_approver = cls.env["res.users"].create({
            "name": "Jefe Aprobador",
            "login": "approver_test",
            "groups_id": [(6, 0, [group_approver.id])],
        })
        cls.user_treasury = cls.env["res.users"].create({
            "name": "Encargado Tesoreria",
            "login": "treasury_test",
            "groups_id": [(6, 0, [group_treasury.id])],
        })

    def _create_request(self, user=None, **kwargs):
        user = user or self.user_applicant
        vals = {
            "partner_id": self.supplier.id,
            "amount": 500.0,
            "concept": "Pago por materiales de oficina",
            "applicant_id": user.id,
        }
        vals.update(kwargs)
        return self.env["payment.request"].with_user(user).create(vals)

    def test_flow_complete_approval_and_payment(self):
        """Valida el ciclo completo de vida de la solicitud: Borrador -> Enviada -> Aprobada -> Pagada."""
        req = self._create_request()
        self.assertEqual(req.state, "draft")
        self.assertTrue(req.name.startswith("SP/"))

        # 1. Enviar solicitud
        req.action_send()
        self.assertEqual(req.state, "sent")

        # 2. Aprobar solicitud por el aprobador
        req.with_user(self.user_approver).action_approve()
        self.assertEqual(req.state, "approved")

        # 3. Registrar pago por tesorería
        req.with_user(self.user_treasury).action_pay()
        self.assertEqual(req.state, "paid")

    def test_negative_or_zero_amount_raises_error(self):
        """Valida que no se permitan montos cero o negativos."""
        with self.assertRaises(ValidationError):
            self._create_request(amount=0)

        with self.assertRaises(ValidationError):
            self._create_request(amount=-250.50)

    def test_applicant_cannot_approve(self):
        """Valida que el solicitante no puede aprobar ni directa ni programáticamente su solicitud."""
        req = self._create_request()
        req.action_send()

        # 1. El solicitante regular intenta llamar action_approve -> AccessError (no tiene grupo aprobador)
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant).action_approve()

        # 2. Un usuario aprobador que es el solicitante intenta auto-aprobarse -> UserError
        req_self = self._create_request(user=self.user_approver)
        req_self.action_send()
        with self.assertRaises(UserError):
            req_self.with_user(self.user_approver).action_approve()

    def test_sent_request_is_immutable(self):
        """Valida que una vez enviada, los campos en el formulario queden en solo lectura."""
        req = self._create_request()
        req.action_send()

        with Form(req.with_user(self.user_applicant)) as form:
            with self.assertRaises(AssertionError):
                form.amount = 1000.0
            with self.assertRaises(AssertionError):
                form.concept = "Modificación no autorizada"

    def test_applicant_sees_only_own_requests(self):
        """Valida la regla de registro (ir.rule): el solicitante solo ve sus registros."""
        req1 = self._create_request(user=self.user_applicant, concept="Solicitud 1")
        req2 = self._create_request(user=self.user_other_applicant, concept="Solicitud 2")

        # Solicitante 1 buscando solicitudes
        visible_user1 = self.env["payment.request"].with_user(self.user_applicant).search([])
        self.assertIn(req1, visible_user1)
        self.assertNotIn(req2, visible_user1)

        # Aprobador buscando solicitudes: debe ver ambas
        visible_approver = self.env["payment.request"].with_user(self.user_approver).search([])
        self.assertIn(req1, visible_approver)
        self.assertIn(req2, visible_approver)

    def test_cannot_delete_unless_draft(self):
        """Valida que no se pueda eliminar una solicitud que no esté en borrador."""
        req = self._create_request()
        req.action_send()

        with self.assertRaises(UserError):
            req.unlink()

    def test_rejection_and_reset_draft_flow(self):
        """Valida el flujo de rechazo y restauración a borrador."""
        req = self._create_request()
        req.action_send()

        # Aprobador rechaza
        req.with_user(self.user_approver).action_reject()
        self.assertEqual(req.state, "rejected")

        # Solicitante la restablece a borrador para corregirla
        req.with_user(self.user_applicant).action_reset_draft()
        self.assertEqual(req.state, "draft")
