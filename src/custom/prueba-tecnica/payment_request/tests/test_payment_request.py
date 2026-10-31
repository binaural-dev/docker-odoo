from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    """Pruebas unitarias para el módulo payment_request (Tramo A)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Usuario Solicitante (Empleado)
        cls.solicitante_a = new_test_user(
            cls.env,
            login="solicitante_a",
            groups="payment_request.group_payment_request_user",
            name="Empleado Solicitante A",
        )
        cls.solicitante_b = new_test_user(
            cls.env,
            login="solicitante_b",
            groups="payment_request.group_payment_request_user",
            name="Empleado Solicitante B",
        )
        # Usuario Aprobador (Jefe / Gerente)
        cls.aprobador = new_test_user(
            cls.env,
            login="aprobador",
            groups="payment_request.group_payment_request_approver",
            name="Jefe Aprobador",
        )
        # Usuario Tesorería
        cls.tesoreria = new_test_user(
            cls.env,
            login="tesoreria",
            groups="payment_request.group_payment_request_treasury",
            name="Encargado Tesorería",
        )
        # Proveedor de prueba
        cls.partner = cls.env["res.partner"].create({"name": "Proveedor Central S.A."})
        cls.currency = cls.env.company.currency_id

    def _create_request(self, user, amount=500.0, concept="Pago de servicios de mantenimiento"):
        """Helper para crear una solicitud en nombre de un usuario."""
        return (
            self.env["payment.request"]
            .with_user(user)
            .create({
                "partner_id": self.partner.id,
                "amount": amount,
                "currency_id": self.currency.id,
                "concept": concept,
            })
        )

    def test_happy_path(self):
        """Flujo completo feliz: Borrador -> Enviada -> Aprobada -> Pagada."""
        # 1. Creación en borrador por el solicitante
        req = self._create_request(self.solicitante_a, amount=1200.0)
        self.assertEqual(req.state, "draft")
        self.assertTrue(req.name.startswith("SP/"))
        self.assertEqual(req.user_id, self.solicitante_a)

        # 2. El solicitante envía la solicitud
        req.with_user(self.solicitante_a).action_submit()
        self.assertEqual(req.state, "submitted")

        # 3. El aprobador aprueba la solicitud
        req.with_user(self.aprobador).action_approve()
        self.assertEqual(req.state, "approved")

        # 4. Tesorería procesa el pago
        req.with_user(self.tesoreria).action_pay()
        self.assertEqual(req.state, "paid")

    def test_solicitante_cannot_approve(self):
        """Seguridad: Un solicitante no puede aprobar su solicitud, ni desde botón ni llamando al método."""
        req = self._create_request(self.solicitante_a, amount=300.0)
        req.with_user(self.solicitante_a).action_submit()

        # El solicitante intenta invocar action_approve(): debe fallar con AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.solicitante_a).action_approve()

        # El estado debe continuar en 'submitted'
        self.assertEqual(req.state, "submitted")

    def test_solicitante_cannot_pay(self):
        """Seguridad: Ni el solicitante ni el aprobador pueden marcar como pagada una solicitud."""
        req = self._create_request(self.solicitante_a, amount=300.0)
        req.with_user(self.solicitante_a).action_submit()
        req.with_user(self.aprobador).action_approve()

        # Solicitante intenta pagar
        with self.assertRaises(AccessError):
            req.with_user(self.solicitante_a).action_pay()

        # Aprobador intenta pagar
        with self.assertRaises(AccessError):
            req.with_user(self.aprobador).action_pay()

        self.assertEqual(req.state, "approved")

    def test_record_rule_isolation(self):
        """Reglas de Registro: El solicitante A solo ve sus solicitudes y no las del solicitante B."""
        req_a = self._create_request(self.solicitante_a, amount=100.0, concept="Solicitud A")
        req_b = self._create_request(self.solicitante_b, amount=200.0, concept="Solicitud B")

        # Solicitante A busca solicitudes
        requests_a = self.env["payment.request"].with_user(self.solicitante_a).search([])
        self.assertIn(req_a, requests_a)
        self.assertNotIn(req_b, requests_a)

        # El Aprobador ve todas
        requests_aprobador = self.env["payment.request"].with_user(self.aprobador).search([])
        self.assertIn(req_a, requests_aprobador)
        self.assertIn(req_b, requests_aprobador)

        # Tesorería ve todas
        requests_tesoreria = self.env["payment.request"].with_user(self.tesoreria).search([])
        self.assertIn(req_a, requests_tesoreria)
        self.assertIn(req_b, requests_tesoreria)

    def test_amount_positive_constraint(self):
        """Restricción: El monto debe ser estrictamente mayor a cero."""
        with self.assertRaises(ValidationError):
            self._create_request(self.solicitante_a, amount=0.0)

        with self.assertRaises(ValidationError):
            self._create_request(self.solicitante_a, amount=-50.0)

    def test_cannot_edit_submitted_request(self):
        """Integridad: Una solicitud enviada no puede ser modificada."""
        req = self._create_request(self.solicitante_a, amount=500.0)
        req.with_user(self.solicitante_a).action_submit()

        # Intentar modificar el monto una vez enviada
        with self.assertRaises(UserError):
            req.with_user(self.solicitante_a).write({"amount": 800.0})

        # Intentar modificar el proveedor
        other_partner = self.env["res.partner"].create({"name": "Otro Proveedor"})
        with self.assertRaises(UserError):
            req.with_user(self.solicitante_a).write({"partner_id": other_partner.id})

    def test_rejection_and_reset_to_draft(self):
        """Flujo de rechazo por aprobador y reinicio a borrador."""
        req = self._create_request(self.solicitante_a, amount=450.0)
        req.with_user(self.solicitante_a).action_submit()

        # Aprobador rechaza
        req.with_user(self.aprobador).action_reject()
        self.assertEqual(req.state, "rejected")

        # Se restablece a borrador para corregir
        req.with_user(self.solicitante_a).action_draft()
        self.assertEqual(req.state, "draft")

        # Ahora en borrador sí se puede editar el concepto o monto
        req.with_user(self.solicitante_a).write({"amount": 400.0})
        self.assertEqual(req.amount, 400.0)
