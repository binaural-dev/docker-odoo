"""Migración 18.0.1.0.0 -> 18.0.1.1.0: tipo de vehículo de selección a catálogo (many2one).

Lo llaman migrations/18.0.1.1.0/pre-migrate.py y post-migrate.py. Está en un módulo aparte para poder
probarlo (tests/test_vehicle_type_migration.py).

- Idempotente: cada paso solo toca las filas que todavía no procesó, así que correrlo dos veces (o retomarlo
  después de un corte) deja el mismo resultado.
- Por lotes: cada UPDATE procesa como máximo `batch_size` filas, recorriendo la tabla por id desde el último
  lote (no vuelve a leer lo ya procesado). Solo los ids del lote pasan por Python, así que la
  memoria del proceso no crece con la cantidad de inspecciones. Toda la actualización de Odoo sigue siendo
  una sola transacción (si algo falla, se deshace completa); los lotes acotan cada sentencia y permiten ver
  el avance en el registro.
"""
import logging
import resource
import time

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

TABLE = "fleet_inspection"
OLD_COLUMN = "vehicle_type"
LEGACY_COLUMN = "legacy_vehicle_type"
BATCH_SIZE = 1000


def _max_rss_mb():
    """Memoria máxima (RSS) usada por el proceso hasta ahora, en MB (Linux informa KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _run_in_batches(cr, pending_where, update_sql, batch_size, label):
    """Procesa por lotes las filas que cumplen `pending_where`, recorriéndolas por id (paginación por clave).

    Cada lote toma los siguientes `batch_size` ids pendientes a partir del último procesado, así que nunca
    vuelve a recorrer lo ya hecho: el costo crece en proporción al volumen. En memoria solo hay los ids del
    lote. `update_sql` recibe los ids del lote en %(ids)s.
    """
    total, batches, last_id, start = 0, 0, 0, time.perf_counter()
    while True:
        cr.execute(f"""
            SELECT id FROM "{TABLE}"
             WHERE id > %(last_id)s AND ({pending_where})
             ORDER BY id LIMIT %(batch_size)s
        """, {"last_id": last_id, "batch_size": batch_size})
        ids = [row[0] for row in cr.fetchall()]
        if not ids:
            break
        cr.execute(update_sql, {"ids": ids})
        last_id = ids[-1]
        total += cr.rowcount
        batches += 1
        _logger.info("fleet_inspection: %s: lote %s, %s filas (acumulado %s, %.2f s)",
                     label, batches, cr.rowcount, total, time.perf_counter() - start)
    return total, batches, time.perf_counter() - start


def save_legacy_vehicle_type(cr, batch_size=BATCH_SIZE):
    """pre-migrate: copia la selección a una columna propia.

    Al terminar la actualización, Odoo borra la columna de un campo que ya no existe en el modelo; esta
    copia sobrevive y queda como respaldo para verificar y, si hiciera falta, revertir.
    """
    if not column_exists(cr, TABLE, OLD_COLUMN):
        _logger.info("fleet_inspection: no hay columna %s, nada que respaldar", OLD_COLUMN)
        return 0
    if not column_exists(cr, TABLE, LEGACY_COLUMN):
        cr.execute(f'ALTER TABLE "{TABLE}" ADD COLUMN "{LEGACY_COLUMN}" varchar')
    # Solo filas sin respaldo: correrlo dos veces no pisa nada.
    total, batches, seconds = _run_in_batches(
        cr,
        f'"{LEGACY_COLUMN}" IS NULL AND "{OLD_COLUMN}" IS NOT NULL',
        f'UPDATE "{TABLE}" SET "{LEGACY_COLUMN}" = "{OLD_COLUMN}" WHERE id = ANY(%(ids)s)',
        batch_size, "respaldo",
    )
    _logger.info("fleet_inspection: %s inspecciones respaldadas en %s (%s lotes, %.2f s, memoria máx. %.0f MB)",
                 total, LEGACY_COLUMN, batches, seconds, _max_rss_mb())
    return total


def assign_vehicle_types(env, batch_size=BATCH_SIZE):
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

    total, batches, seconds = _run_in_batches(
        cr,
        f'vehicle_type_id IS NULL AND "{LEGACY_COLUMN}" IS NOT NULL',
        f"""
        UPDATE "{TABLE}" i SET vehicle_type_id = t.id
          FROM fleet_inspection_vehicle_type t
         WHERE t.code = i."{LEGACY_COLUMN}" AND i.id = ANY(%(ids)s)
        """,
        batch_size, "asignación",
    )
    result["assigned"] = total
    env.invalidate_all()

    cr.execute(f'SELECT count(*) FROM "{TABLE}" WHERE vehicle_type_id IS NULL')
    missing = cr.fetchone()[0]
    if missing:
        raise RuntimeError(
            f"fleet_inspection: {missing} inspecciones quedaron sin tipo de vehículo; se aborta la actualización"
        )
    _logger.info("fleet_inspection: %s inspecciones con tipo asignado (%s lotes, %.2f s, memoria máx. %.0f MB); "
                 "tipos creados: %s", total, batches, seconds, _max_rss_mb(), result["created_types"] or "ninguno")
    return result
