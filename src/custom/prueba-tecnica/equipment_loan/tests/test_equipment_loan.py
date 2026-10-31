from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestEquipmentLoan(TransactionCase):
    """Pruebas unitarias para el módulo equipment_loan."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_operator = new_test_user(
            cls.env,
            login="operator_user",
            groups="equipment_loan.group_equipment_loan_manager",
            name="Operador TI",
        )
        cls.receiver_partner = cls.env["res.partner"].create({
            "name": "Ana Gómez - Consultora",
            "email": "ana.gomez@example.com",
        })
        cls.laptop_1 = cls.env["equipment.laptop"].create({
            "name": "MacBook Air M2 - TI-01",
            "serial_number": "SN-MAC-M2-001",
            "brand": "Apple",
            "model": "MacBook Air M2 2023",
        })
        cls.laptop_2 = cls.env["equipment.laptop"].create({
            "name": "Dell Latitude 5420 - TI-02",
            "serial_number": "SN-DELL-LAT-002",
            "brand": "Dell",
            "model": "Latitude 5420",
        })

    def test_01_happy_path_loan_and_return(self):
        """Ciclo de vida completo: Borrador -> Entregar (Prestado) -> Devolver (Devuelto)."""
        today = fields.Date.context_today(self.env.user)
        next_week = today + timedelta(days=7)

        # 1. Creación en Borrador
        loan = self.env["equipment.loan"].with_user(self.user_operator).create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": next_week,
        })
        self.assertEqual(loan.state, "draft")
        self.assertTrue(loan.name.startswith("PREST/"))
        self.assertEqual(self.laptop_1.state, "available")
        self.assertFalse(loan.actual_return_date)

        # 2. Entregar el equipo
        loan.action_deliver()
        self.assertEqual(loan.state, "loaned")
        self.assertEqual(self.laptop_1.state, "loaned")
        self.assertEqual(loan.delivery_date, today)

        # 3. Devolver el equipo
        loan.action_return()
        self.assertEqual(loan.state, "returned")
        self.assertEqual(self.laptop_1.state, "available")
        self.assertEqual(loan.actual_return_date, today)

    def test_02_actual_return_date_recorded_automatically(self):
        """El botón Devolver debe fijar la fecha real del día automáticamente."""
        today = fields.Date.context_today(self.env.user)
        loan = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_2.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=5),
        })
        loan.action_deliver()
        self.assertFalse(loan.actual_return_date)

        loan.action_return()
        self.assertEqual(loan.actual_return_date, today)

    def test_03_sequential_loans_allowed_and_simultaneous_loans_blocked(self):
        """Un equipo puede tener múltiples préstamos sucesivos a lo largo de su vida útil,
        pero no puede estar prestado a dos personas ni tener préstamos activos al mismo tiempo."""
        today = fields.Date.context_today(self.env.user)

        # Préstamo 1: entregado y devuelto
        loan_1 = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=2),
        })
        loan_1.action_deliver()
        loan_1.action_return()
        self.assertEqual(loan_1.state, "returned")

        # Préstamo 2: entregado y devuelto
        loan_2 = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=3),
        })
        loan_2.action_deliver()
        loan_2.action_return()
        self.assertEqual(loan_2.state, "returned")

        # Préstamo 3: Debe permitirse crear y entregar exitosamente porque los anteriores fueron devueltos
        loan_3 = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=4),
        })
        loan_3.action_deliver()
        self.assertEqual(loan_3.state, "loaned")

        # Intento de segundo préstamo activo simultáneo (a otra persona o a la misma):
        # Debe fallar con ValidationError / UserError
        second_receiver = self.env["res.partner"].create({"name": "Carlos Méndez"})
        loan_concurrent = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": second_receiver.id,
            "expected_return_date": today + timedelta(days=5),
        })

        # Al intentar entregar teniendo loan_3 activo:
        with self.assertRaises(UserError):
            loan_concurrent.action_deliver()

        # O al intentar forzar el estado a 'loaned' directamente por ORM:
        with self.assertRaises(ValidationError):
            loan_concurrent.write({"state": "loaned"})

    def test_04_overdue_computation_and_search(self):
        """Un préstamo está vencido si su fecha previa ya pasó y continúa en estado 'loaned'."""
        today = fields.Date.context_today(self.env.user)
        past_date = today - timedelta(days=2)

        loan = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "delivery_date": today - timedelta(days=5),
            "expected_return_date": past_date,
        })
        loan.action_deliver()

        # Al estar en 'loaned' y con fecha previa vencida, is_overdue debe ser True
        self.assertTrue(loan.is_overdue)

        # Verificación del filtro de búsqueda
        overdue_loans = self.env["equipment.loan"].search([("is_overdue", "=", True)])
        self.assertIn(loan, overdue_loans)

        # Al devolverlo, deja de considerarse vencido
        loan.action_return()
        self.assertFalse(loan.is_overdue)

    def test_05_single_active_loan_concurrency(self):
        """No se puede entregar un equipo si ya se encuentra en un préstamo activo."""
        today = fields.Date.context_today(self.env.user)

        loan_a = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=4),
        })
        loan_b = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=5),
        })

        # Entregar préstamo A con éxito
        loan_a.action_deliver()
        self.assertEqual(self.laptop_1.state, "loaned")

        # Intentar entregar préstamo B para el mismo equipo mientras está prestado: Debe fallar
        with self.assertRaises(UserError):
            loan_b.action_deliver()

    def test_06_dates_consistency_constraint(self):
        """La fecha previa de devolución no puede ser anterior a la fecha de entrega."""
        today = fields.Date.context_today(self.env.user)
        with self.assertRaises(ValidationError):
            self.env["equipment.loan"].create({
                "laptop_id": self.laptop_1.id,
                "receiver_id": self.receiver_partner.id,
                "delivery_date": today,
                "expected_return_date": today - timedelta(days=1),
            })

    def test_07_immutability_after_delivery(self):
        """No se pueden modificar datos esenciales una vez entregado el equipo."""
        today = fields.Date.context_today(self.env.user)
        loan = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=5),
        })
        loan.action_deliver()

        # Intentar cambiar la persona receptora o el equipo debe fallar
        with self.assertRaises(UserError):
            loan.write({"receiver_id": self.env.user.partner_id.id})

    def test_08_laptop_history_action(self):
        """El botón de historial retorna la acción de ventana correctamente configurada."""
        today = fields.Date.context_today(self.env.user)
        loan = self.env["equipment.loan"].create({
            "laptop_id": self.laptop_1.id,
            "receiver_id": self.receiver_partner.id,
            "expected_return_date": today + timedelta(days=5),
        })
        action = loan.action_view_laptop_history()
        self.assertEqual(action["res_model"], "equipment.loan")
        self.assertIn(("laptop_id", "=", self.laptop_1.id), action["domain"])

