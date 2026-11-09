from odoo.tests import TransactionCase, tagged

from odoo.addons.fleet_inspection.migration_utils import (
    LEGACY_COLUMN,
    assign_vehicle_types,
    save_legacy_vehicle_type,
)


@tagged("post_install", "-at_install")
class TestVehicleTypeMigration(TransactionCase):
    """Lógica de migrations/18.0.1.1.0 sobre la tabla tal como quedaba en la 18.0.1.0.0.

    Los cambios de esquema (ALTER TABLE) se deshacen al final de la prueba, como todo en TransactionCase.
    """

    OLD_VALUES = ["motorcycle", "car", "truck", "other", "other", "trailer"]  # «trailer»: fuera del catálogo

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Marca"})
        model = cls.env["fleet.vehicle.model"].create({"name": "Modelo", "brand_id": brand.id})
        vehicle = cls.env["fleet.vehicle"].create({"model_id": model.id, "license_plate": "MIG001"})
        cls.inspections = cls.env["fleet.inspection"].create([{"vehicle_id": vehicle.id} for _ in cls.OLD_VALUES])
        cls.env.flush_all()

    def _simulate_v1_0_0(self):
        """Columna de selección con valores y many2one vacío, como al empezar la actualización."""
        cr = self.env.cr
        cr.execute("ALTER TABLE fleet_inspection ADD COLUMN vehicle_type varchar")
        cr.execute("ALTER TABLE fleet_inspection ALTER COLUMN vehicle_type_id DROP NOT NULL")
        for inspection, value in zip(self.inspections, self.OLD_VALUES):
            cr.execute(
                "UPDATE fleet_inspection SET vehicle_type = %s, vehicle_type_id = NULL WHERE id = %s",
                (value, inspection.id),
            )
        self.env.invalidate_all()

    def _type_codes(self):
        self.env.invalidate_all()
        return self.inspections.mapped(lambda i: i.vehicle_type_id.code)

    def test_every_inspection_keeps_its_type(self):
        self._simulate_v1_0_0()
        self.assertEqual(save_legacy_vehicle_type(self.env.cr), len(self.OLD_VALUES))
        result = assign_vehicle_types(self.env)

        self.assertEqual(self._type_codes(), self.OLD_VALUES)
        self.assertEqual(result["assigned"], len(self.OLD_VALUES))
        # Los tipos iniciales son los del catálogo (no duplicados), incluido «otro».
        self.assertEqual(self.inspections[0].vehicle_type_id, self.env.ref("fleet_inspection.vehicle_type_motorcycle"))
        self.assertEqual(self.inspections[3].vehicle_type_id, self.env.ref("fleet_inspection.vehicle_type_other"))
        self.assertEqual(self.inspections[4].vehicle_type_id, self.env.ref("fleet_inspection.vehicle_type_other"))
        # El valor desconocido no se pierde ni se convierte en «otro».
        self.assertEqual(result["created_types"], ["trailer"])
        self.assertEqual(self.inspections[5].vehicle_type_id.code, "trailer")
        self.env.cr.execute("SELECT count(*) FROM fleet_inspection WHERE vehicle_type_id IS NULL")
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_small_batches_give_the_same_result(self):
        """Con lotes de 2 filas, las 6 inspecciones se procesan en 3 lotes por paso y el resultado no cambia."""
        self._simulate_v1_0_0()
        with self.assertLogs("odoo.addons.fleet_inspection.migration_utils", level="INFO") as logs:
            self.assertEqual(save_legacy_vehicle_type(self.env.cr, batch_size=2), len(self.OLD_VALUES))
            result = assign_vehicle_types(self.env, batch_size=2)
        self.assertEqual(result["assigned"], len(self.OLD_VALUES))
        self.assertEqual(self._type_codes(), self.OLD_VALUES)
        self.assertEqual(sum("respaldo: lote" in line for line in logs.output), 3)
        self.assertEqual(sum("asignación: lote" in line for line in logs.output), 3)

    def test_resumes_after_a_partial_run(self):
        """Si una corrida anterior quedó a medias, la siguiente completa solo lo que faltaba."""
        self._simulate_v1_0_0()
        save_legacy_vehicle_type(self.env.cr)
        # Simula que solo se alcanzaron a procesar las dos primeras inspecciones.
        self.env.cr.execute(
            "UPDATE fleet_inspection i SET vehicle_type_id = t.id FROM fleet_inspection_vehicle_type t"
            f" WHERE t.code = i.{LEGACY_COLUMN} AND i.id = ANY(%s)",
            (self.inspections[:2].ids,),
        )
        result = assign_vehicle_types(self.env)
        self.assertEqual(result["assigned"], len(self.OLD_VALUES) - 2)
        self.assertEqual(self._type_codes(), self.OLD_VALUES)

    def test_running_twice_changes_nothing(self):
        self._simulate_v1_0_0()
        save_legacy_vehicle_type(self.env.cr)
        assign_vehicle_types(self.env)
        types_before = self.env["fleet.inspection.vehicle.type"].with_context(active_test=False).search_count([])

        self.assertEqual(save_legacy_vehicle_type(self.env.cr), 0, "No vuelve a respaldar lo ya respaldado")
        result = assign_vehicle_types(self.env)
        self.assertEqual(result, {"created_types": [], "assigned": 0})
        self.assertEqual(self._type_codes(), self.OLD_VALUES)
        self.assertEqual(
            self.env["fleet.inspection.vehicle.type"].with_context(active_test=False).search_count([]), types_before
        )

    def test_rerun_does_not_overwrite_manual_corrections(self):
        self._simulate_v1_0_0()
        save_legacy_vehicle_type(self.env.cr)
        assign_vehicle_types(self.env)
        self.inspections[0].vehicle_type_id = self.env.ref("fleet_inspection.vehicle_type_car")
        self.env.flush_all()
        assign_vehicle_types(self.env)
        self.assertEqual(self._type_codes()[0], "car")

    def test_aborts_if_an_inspection_would_stay_without_type(self):
        self._simulate_v1_0_0()
        save_legacy_vehicle_type(self.env.cr)
        self.env.cr.execute(
            f"UPDATE fleet_inspection SET {LEGACY_COLUMN} = NULL WHERE id = %s", (self.inspections[0].id,)
        )
        with self.assertRaises(RuntimeError):
            assign_vehicle_types(self.env)

    def test_fresh_install_has_nothing_to_migrate(self):
        """En una base nueva no hay columna anterior: los scripts no hacen nada."""
        self.assertEqual(save_legacy_vehicle_type(self.env.cr), 0)
        self.assertEqual(assign_vehicle_types(self.env), {"created_types": [], "assigned": 0})
