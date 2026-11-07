import sys
from importlib import import_module
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFleetInspectionMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Marca Migración"})
        model = cls.env["fleet.vehicle.model"].create({"name": "Modelo Migración", "brand_id": brand.id})
        cls.vehicle = cls.env["fleet.vehicle"].create({"model_id": model.id, "license_plate": "MIG-001"})
        cls.inspector = cls.env["res.users"].create({
            "name": "Inspector Migración",
            "login": "inspector_mig",
            "groups_id": [(6, 0, [cls.env.ref("fleet_inspection.group_fleet_inspection_user").id])],
        })

    def _get_migrate_func(self):
        # Carga dinámica del script post-migrate
        script_path = Path(__file__).resolve().parent.parent / "migrations" / "17.0.2.0.0" / "post-migrate.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("post_migrate_17_0_2_0_0", str(script_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.migrate

    def test_migration_selection_to_many2one(self):
        """Valida que la migración transfiera los valores de selección a Many2one sin pérdidas."""
        cr = self.env.cr

        # Crear inspecciones base
        inspections = self.env["fleet.inspection"].create([
            {"vehicle_id": self.vehicle.id, "inspector_id": self.inspector.id},
            {"vehicle_id": self.vehicle.id, "inspector_id": self.inspector.id},
            {"vehicle_id": self.vehicle.id, "inspector_id": self.inspector.id},
            {"vehicle_id": self.vehicle.id, "inspector_id": self.inspector.id},
            {"vehicle_id": self.vehicle.id, "inspector_id": self.inspector.id},
        ])

        # Asegurar columna legacy y relajar NOT NULL temporalmente para simular el estado previo a la migración
        cr.execute("""
            ALTER TABLE fleet_inspection ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR;
            ALTER TABLE fleet_inspection ALTER COLUMN vehicle_type_id DROP NOT NULL;
        """)

        # Asignar estados legacy directamente en SQL simulando v17.0.1.0.0
        codes = ["motorcycle", "car", "truck", "other", "legacy_custom_unknown"]
        for insp, code in zip(inspections, codes):
            cr.execute("""
                UPDATE fleet_inspection 
                SET vehicle_type = %s, vehicle_type_id = NULL 
                WHERE id = %s
            """, (code, insp.id))

        # Verificar que vehicle_type_id está en NULL antes de migrar
        inspections.invalidate_recordset()
        self.assertTrue(all(not insp.vehicle_type_id for insp in inspections))

        # Ejecutar migración
        migrate = self._get_migrate_func()
        migrate(cr, "17.0.1.0.0")

        # Refrescar y validar
        inspections.invalidate_recordset()
        self.assertTrue(all(insp.vehicle_type_id for insp in inspections), "Ninguna inspección debe quedar sin tipo")

        self.assertEqual(inspections[0].vehicle_type_id.code, "motorcycle")
        self.assertEqual(inspections[1].vehicle_type_id.code, "car")
        self.assertEqual(inspections[2].vehicle_type_id.code, "truck")
        self.assertEqual(inspections[3].vehicle_type_id.code, "other")
        # El valor desconocido se preserva asignándose a 'other'
        self.assertEqual(inspections[4].vehicle_type_id.code, "other")

        # Probar IDEMPOTENCIA: correr la migración una segunda vez
        migrate(cr, "17.0.1.0.0")
        inspections.invalidate_recordset()
        self.assertEqual(inspections[0].vehicle_type_id.code, "motorcycle")
        self.assertEqual(inspections[1].vehicle_type_id.code, "car")
        self.assertEqual(inspections[2].vehicle_type_id.code, "truck")
        self.assertEqual(inspections[3].vehicle_type_id.code, "other")
        self.assertEqual(inspections[4].vehicle_type_id.code, "other")
