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

        # Grupo Solicitante, Aprobador y Tesorería
        group_user = cls.env.ref("payment_request.group_payment_request_user")
        group_approver = cls.env.ref("payment_request.group_payment_request_approver")
        group_treasury = cls.env.ref("payment_request.group_payment_request_treasury")

        if not cls.env.company.email:
            cls.env.company.email = "company@test.com"

        cls.user_applicant = cls.env["res.users"].create({
            "name": "Empleado Solicitante",
            "login": "applicant_test",
            "email": "applicant@test.com",
            "groups_id": [(6, 0, [group_user.id])],
        })
        cls.user_other_applicant = cls.env["res.users"].create({
            "name": "Otro Empleado",
            "login": "other_applicant_test",
            "email": "other_applicant@test.com",
            "groups_id": [(6, 0, [group_user.id])],
        })
        cls.user_approver = cls.env["res.users"].create({
            "name": "Jefe Aprobador",
            "login": "approver_test",
            "email": "approver@test.com",
            "groups_id": [(6, 0, [group_approver.id])],
        })
        cls.user_manager = cls.env["res.users"].create({
            "name": "Gerente General",
            "login": "manager_test",
            "email": "manager@test.com",
            "groups_id": [(6, 0, [group_approver.id])],
        })
        cls.user_treasury = cls.env["res.users"].create({
            "name": "Encargado Tesorería",
            "login": "treasury_test",
            "email": "treasury@test.com",
            "groups_id": [(6, 0, [group_treasury.id])],
        })

        # Diario bancario para pagos
        cls.bank_journal = cls.env["account.journal"].search([
            ("type", "in", ("bank", "cash")),
            ("company_id", "=", cls.env.company.id),
        ], limit=1)
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create({
                "name": "Banco Test",
                "code": "BNKT",
                "type": "bank",
                "company_id": cls.env.company.id,
            })

        # Niveles de aprobación configurables:
        # Nivel 1: Jefe de Área para montos >= 0
        cls.level_low = cls.env["payment.approval.level"].create({
            "name": "Jefe de Área",
            "amount_min": 0.0,
            "approver_id": cls.user_approver.id,
            "company_id": cls.env.company.id,
            "sequence": 20,
        })
        # Nivel 2: Gerencia General para montos >= 1000
        cls.level_high = cls.env["payment.approval.level"].create({
            "name": "Gerencia General",
            "amount_min": 1000.0,
            "approver_id": cls.user_manager.id,
            "company_id": cls.env.company.id,
            "sequence": 10,
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

        # 1. Enviar solicitud (asigna aprobador y crea actividad)
        req.action_send()
        self.assertEqual(req.state, "sent")
        self.assertEqual(req.approver_id, self.user_approver)

        # 2. Aprobar solicitud por el aprobador asignado
        req.with_user(self.user_approver).action_approve()
        self.assertEqual(req.state, "approved")
        self.assertEqual(req.approver_user_id, self.user_approver)
        self.assertTrue(req.approval_date)

        # 3. Registrar pago mediante wizard de tesorería
        pay_wizard = self.env["payment.request.pay.wizard"].with_user(self.user_treasury).create({
            "request_id": req.id,
            "journal_id": self.bank_journal.id,
        })
        pay_wizard.action_confirm_payment()
        self.assertEqual(req.state, "paid")
        self.assertTrue(req.payment_id)
        self.assertEqual(req.sudo().payment_id.state, "posted")
        self.assertEqual(req.sudo().payment_id.amount, 500.0)

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

        visible_user1 = self.env["payment.request"].with_user(self.user_applicant).search([])
        self.assertIn(req1, visible_user1)
        self.assertNotIn(req2, visible_user1)

        visible_approver = self.env["payment.request"].with_user(self.user_approver).search([])
        self.assertIn(req1, visible_approver)
        self.assertIn(req2, visible_approver)

    def test_cannot_delete_unless_draft(self):
        """Valida que no se pueda eliminar una solicitud que no esté en borrador."""
        req = self._create_request()
        req.action_send()

        with self.assertRaises(UserError):
            req.unlink()

    def test_approval_levels_and_activity_assignment(self):
        """Valida asignación dinámica de aprobadores según montos y creación de actividad."""
        # Solicitud normal (< 1000) -> Jefe Aprobador
        req_low = self._create_request(amount=350.0)
        req_low.action_send()
        self.assertEqual(req_low.approver_id, self.user_approver)

        activities_low = self.env["mail.activity"].search([
            ("res_model", "=", "payment.request"),
            ("res_id", "=", req_low.id),
            ("user_id", "=", self.user_approver.id),
        ])
        self.assertTrue(activities_low, "Debe haberse generado una actividad para el Jefe Aprobador")

        # Solicitud alta (>= 1000) -> Gerencia General
        req_high = self._create_request(amount=2500.0)
        req_high.action_send()
        self.assertEqual(req_high.approver_id, self.user_manager)

        activities_high = self.env["mail.activity"].search([
            ("res_model", "=", "payment.request"),
            ("res_id", "=", req_high.id),
            ("user_id", "=", self.user_manager.id),
        ])
        self.assertTrue(activities_high, "Debe haberse generado una actividad para la Gerencia General")

    def test_only_assigned_approver_can_approve(self):
        """Valida que solo el aprobador específicamente asignado a la solicitud puede aprobarla."""
        req_high = self._create_request(amount=3000.0)
        req_high.action_send()
        self.assertEqual(req_high.approver_id, self.user_manager)

        # El jefe intenta aprobar la solicitud de la gerencia -> UserError
        with self.assertRaises(UserError):
            req_high.with_user(self.user_approver).action_approve()

        # La gerencia (aprobador asignado) aprueba -> Éxito
        req_high.with_user(self.user_manager).action_approve()
        self.assertEqual(req_high.state, "approved")
        self.assertEqual(req_high.approver_user_id, self.user_manager)

    def test_rejection_wizard_with_reason_in_chatter(self):
        """Valida que el rechazo requiera motivo obligatorio y lo publique en el chatter."""
        req = self._create_request(amount=400.0)
        req.action_send()

        # Intento de rechazo por un aprobador no asignado
        with self.assertRaises(UserError):
            wizard_unauth = self.env["payment.request.reject.wizard"].with_user(self.user_manager).create({
                "request_id": req.id,
                "reason": "Intento no autorizado",
            })
            wizard_unauth.action_confirm_reject()

        # Intento de rechazo sin motivo
        with self.assertRaises(UserError):
            wizard_empty = self.env["payment.request.reject.wizard"].with_user(self.user_approver).create({
                "request_id": req.id,
                "reason": "   ",
            })
            wizard_empty.action_confirm_reject()

        # Rechazo exitoso con motivo justificado
        wizard = self.env["payment.request.reject.wizard"].with_user(self.user_approver).create({
            "request_id": req.id,
            "reason": "Monto no contemplado en el presupuesto del departamento.",
        })
        wizard.action_confirm_reject()

        self.assertEqual(req.state, "rejected")
        self.assertEqual(req.reject_reason, "Monto no contemplado en el presupuesto del departamento.")

        # Verificar publicación en el chatter
        messages = req.message_ids.mapped("body")
        self.assertTrue(
            any("Monto no contemplado en el presupuesto" in msg for msg in messages),
            "El motivo de rechazo debe quedar visible en el chatter",
        )

        # Restaurar a borrador tras rechazo
        req.with_user(self.user_applicant).action_reset_draft()
        self.assertEqual(req.state, "draft")

    def test_cannot_pay_twice(self):
        """Valida explícitamente que una solicitud no puede ser pagada dos veces."""
        req = self._create_request(amount=800.0)
        req.action_send()
        req.with_user(self.user_approver).action_approve()

        # 1er Pago exitoso
        pay_wizard = self.env["payment.request.pay.wizard"].with_user(self.user_treasury).create({
            "request_id": req.id,
            "journal_id": self.bank_journal.id,
        })
        pay_wizard.action_confirm_payment()
        self.assertEqual(req.state, "paid")
        first_payment_id = req.payment_id.id

        # 2do intento: llamar al botón action_pay -> UserError
        with self.assertRaises(UserError):
            req.with_user(self.user_treasury).action_pay()

        # 2do intento: invocar directamente el wizard de pago -> UserError
        second_wizard = self.env["payment.request.pay.wizard"].with_user(self.user_treasury).create({
            "request_id": req.id,
            "journal_id": self.bank_journal.id,
        })
        with self.assertRaises(UserError):
            second_wizard.action_confirm_payment()

        # El pago registrado no debe haber cambiado
        self.assertEqual(req.payment_id.id, first_payment_id)

    def test_pdf_report_generation(self):
        """Valida que el reporte PDF QWeb se genere correctamente mostrando quién aprobó y cuándo."""
        req = self._create_request(amount=1200.0)
        req.action_send()
        req.with_user(self.user_manager).action_approve()

        pdf_content, _ = self.env["ir.actions.report"]._render_qweb_pdf(
            "payment_request.action_report_payment_request", req.ids
        )
        self.assertTrue(len(pdf_content) > 0, "El reporte PDF generado no debe estar vacío")

    def test_currency_conversion_usd_to_ves_payment(self):
        """Valida solicitud en USD pagada desde diario en VES aplicando la tasa de la fecha de pago."""
        usd = self.env.ref("base.USD")
        ves = self.env.ref("base.VES")
        ves.active = True

        # Tasa: 1 USD = 36.50 VES (VES tiene tasa 36.50 respecto a la moneda base USD)
        rate = self.env["res.currency.rate"].search([
            ("currency_id", "=", ves.id),
            ("company_id", "=", self.env.company.id),
            ("name", "=", fields.Date.today()),
        ], limit=1)
        if rate:
            rate.write({"rate": 36.50})
        else:
            self.env["res.currency.rate"].create({
                "currency_id": ves.id,
                "company_id": self.env.company.id,
                "name": fields.Date.today(),
                "rate": 36.50,
            })

        journal_ves = self.env["account.journal"].create({
            "name": "Banco en Bolívares Test",
            "code": "BVEST",
            "type": "bank",
            "currency_id": ves.id,
            "company_id": self.env.company.id,
        })

        req = self._create_request(amount=100.0, currency_id=usd.id)
        req.action_send()
        req.with_user(self.user_approver).action_approve()

        # Abrir wizard de pago en diario VES
        pay_wizard = self.env["payment.request.pay.wizard"].with_user(self.user_treasury).create({
            "request_id": req.id,
            "journal_id": journal_ves.id,
            "payment_date": fields.Date.today(),
        })

        # Comprobar monto convertido a la tasa
        self.assertEqual(pay_wizard.payment_amount, 3650.0)
        self.assertAlmostEqual(pay_wizard.exchange_rate, 36.50, places=2)

        # Confirmar pago
        pay_wizard.action_confirm_payment()

        self.assertEqual(req.state, "paid")
        self.assertTrue(req.payment_id)
        self.assertEqual(req.sudo().payment_id.currency_id, ves)
        self.assertEqual(req.sudo().payment_id.amount, 3650.0)
        self.assertEqual(req.payment_amount, 3650.0)
        self.assertEqual(req.payment_currency_id, ves)

    def test_multicompany_isolation_and_access_rules(self):
        """Valida que un usuario de la compañía B no vea solicitudes ni niveles de la compañía A."""
        company_b = self.env["res.company"].create({
            "name": "Distribuidora Andina Sucursal B C.A.",
            "currency_id": self.env.ref("base.USD").id,
        })
        group_user = self.env.ref("payment_request.group_payment_request_user")
        user_b = self.env["res.users"].create({
            "name": "Empleado Sucursal B",
            "login": "applicant_b_test",
            "email": "applicant_b@test.com",
            "company_id": company_b.id,
            "company_ids": [(6, 0, [company_b.id])],
            "groups_id": [(6, 0, [group_user.id])],
        })

        # Solicitud creada en Compañía A
        req_a = self._create_request()
        self.assertEqual(req_a.company_id, self.env.company)

        # 1. Búsqueda desde usuario de Compañía B: no debe listar nada de Compañía A
        visible_requests = self.env["payment.request"].with_user(user_b).search([("id", "=", req_a.id)])
        self.assertFalse(visible_requests, "El usuario de la compañía B no debe ver solicitudes de la compañía A")

        # 2. Intento de lectura directa por ID: debe arrojar AccessError
        with self.assertRaises(AccessError):
            req_a.with_user(user_b).read(["name", "amount", "state"])

    def test_concurrency_database_row_locking(self):
        """Valida que ante concurrencia de aprobadores, el bloqueo de BD (FOR UPDATE NOWAIT) protege el registro."""
        import psycopg2
        from unittest.mock import patch

        req = self._create_request(amount=600.0)
        req.action_send()

        # Simular que otra transacción ya retiene el bloqueo exclusivo de PostgreSQL
        orig_execute = self.cr.execute

        def mock_execute(query, params=None):
            if "FOR UPDATE NOWAIT" in str(query):
                raise psycopg2.OperationalError("could not obtain lock on row in relation payment_request")
            return orig_execute(query, params)

        with patch.object(self.cr, "execute", side_effect=mock_execute):
            with self.assertRaises(UserError) as cm:
                req.with_user(self.user_approver).action_approve()
            self.assertIn("procesada concurrentemente", str(cm.exception))

    def test_payment_creation_failure_does_not_mark_paid(self):
        """Valida que si la creación o validación del pago contable falla, la solicitud no queda en 'paid'."""
        from unittest.mock import patch

        req = self._create_request(amount=750.0)
        req.action_send()
        req.with_user(self.user_approver).action_approve()
        self.assertEqual(req.state, "approved")

        # Simular fallo durante action_post()
        with patch("odoo.addons.account.models.account_payment.AccountPayment.action_post", side_effect=UserError("Error contable simulado")):
            pay_wizard = self.env["payment.request.pay.wizard"].with_user(self.user_treasury).create({
                "request_id": req.id,
                "journal_id": self.bank_journal.id,
            })
            with self.assertRaises(UserError):
                pay_wizard.action_confirm_payment()

        # Verificar inmutabilidad: la solicitud sigue en 'approved' y sin pago asociado
        self.assertEqual(req.state, "approved")
        self.assertFalse(req.payment_id)
