"""Migración 18.0.1.0.0 -> 18.0.1.1.0: tipo de vehículo de selección a catálogo (many2one).

Lo llaman migrations/18.0.1.1.0/pre-migrate.py y post-migrate.py. Está en un módulo aparte para poder
probarlo (tests/test_vehicle_type_migration.py). Ambas funciones son idempotentes.
"""
import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

TABLE = "fleet_inspection"
OLD_COLUMN = "vehicle_type"
LEGACY_COLUMN = "legacy_vehicle_type"


def save_legacy_vehicle_type(cr):
    """pre-migrate: copia la selección a una columna propia.

    Al terminar la actualización, Odoo borra la columna de un campo que ya no existe en el modelo; esta
    copia sobrevive y queda como respaldo para verificar y, si hiciera falta, revertir.
    """
    if not column_exists(cr, TABLE, OLD_COLUMN):
        _logger.info("fleet_inspection: no hay columna %s, nada que respaldar", OLD_COLUMN)
        return 0
    if not column_exists(cr, TABLE, LEGACY_COLUMN):
        cr.execute(f'ALTER TABLE "{TABLE}" ADD COLUMN "{LEGACY_COLUMN}" varchar')
    # Solo las filas que aún no tienen respaldo: correrlo dos veces no pisa nada.
    cr.execute(f"""
        UPDATE "{TABLE}" SET "{LEGACY_COLUMN}" = "{OLD_COLUMN}"
         WHERE "{LEGACY_COLUMN}" IS NULL AND "{OLD_COLUMN}" IS NOT NULL
    """)
    _logger.info("fleet_inspection: %s inspecciones respaldadas en %s", cr.rowcount, LEGACY_COLUMN)
    return cr.rowcount


def assign_vehicle_types(env):
    """post-migrate: relaciona cada inspección con el tipo del catálogo cuyo código es el valor anterior.

    - Un valor que no esté en el catálogo (por ejemplo, agregado a mano en la selección) se crea como tipo
      nuevo con ese código: no se pierde ni se convierte en «otro».
    - Solo toca inspecciones sin tipo: si alguien ya lo corrigió a mano, no se pisa.
    - Si al final queda alguna inspección sin tipo, aborta (y con eso toda la actualización).
    Devuelve un dict con lo que hizo, para el registro y las pruebas.
    """
    cr = env.cr
    result = {"created_types": [], "assigned": 0}
    if not column_exists(cr, TABLE, LEGACY_COLUMN):
        _logger.info("fleet_inspection: no hay columna %s, nada que migrar", LEGACY_COLUMN)
        return result

    VehicleType = env["fleet.inspection.vehicle.type"].with_context(active_test=False)
    cr.execute(f"""
        SELECT DISTINCT i."{LEGACY_COLUMN}"
          FROM "{TABLE}" i
         WHERE i."{LEGACY_COLUMN}" IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM fleet_inspection_vehicle_type t WHERE t.code = i."{LEGACY_COLUMN}")
    """)
    for (code,) in cr.fetchall():
        VehicleType.create({"name": code.replace("_", " ").capitalize(), "code": code})
        result["created_types"].append(code)
        _logger.warning("fleet_inspection: valor «%s» fuera del catálogo; se creó como tipo nuevo", code)
    env.flush_all()

    cr.execute(f"""
        UPDATE "{TABLE}" i SET vehicle_type_id = t.id
          FROM fleet_inspection_vehicle_type t
         WHERE t.code = i."{LEGACY_COLUMN}" AND i.vehicle_type_id IS NULL
    """)
    result["assigned"] = cr.rowcount
    env.invalidate_all()

    cr.execute(f'SELECT count(*) FROM "{TABLE}" WHERE vehicle_type_id IS NULL')
    missing = cr.fetchone()[0]
    if missing:
        raise RuntimeError(
            f"fleet_inspection: {missing} inspecciones quedaron sin tipo de vehículo; se aborta la actualización"
        )
    _logger.info("fleet_inspection: %s inspecciones con tipo asignado; tipos creados: %s",
                 result["assigned"], result["created_types"] or "ninguno")
    return result
