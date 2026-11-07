import json
import logging
import time

_logger = logging.getLogger(__name__)

BATCH_SIZE = 2000

DEFAULT_TYPES = [
    ("motorcycle", "Moto", 10),
    ("car", "Carro", 20),
    ("truck", "Camión", 30),
    ("other", "Otro", 40),
]


def migrate(cr, installed_version):
    """
    Migración a 17.0.2.0.0:
    Convierte el campo legacy 'vehicle_type' (Selection) al nuevo Many2one
    'vehicle_type_id' hacia 'fleet.inspection.vehicle.type'.

    Características:
    - Idempotente: si se ejecuta múltiples veces no altera datos ya migrados ni duplica registros.
    - Procesamiento por lotes (BATCH_SIZE): procesa grandes volúmenes (10.000+) de forma eficiente en memoria.
    - Preserva 'otro' y cualquier valor no reconocido mapeándolo a 'other'.
    """
    start_time = time.time()
    _logger.info("Iniciando migración de fleet_inspection a 17.0.2.0.0 (desde versión %s)", installed_version)

    # 1. Asegurar existencia de la tabla del catálogo
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'fleet_inspection_vehicle_type'
        );
    """)
    if not cr.fetchone()[0]:
        _logger.warning("Tabla 'fleet_inspection_vehicle_type' no encontrada. Se creará en el ciclo normal.")
        return

    # 2. Asegurar que los tipos base existan (idempotente mediante ON CONFLICT o NOT EXISTS)
    # En Odoo 17 los campos translate=True se almacenan como JSONB
    for code, name, sequence in DEFAULT_TYPES:
        json_name = json.dumps({"en_US": name})
        cr.execute("""
            INSERT INTO fleet_inspection_vehicle_type (code, name, sequence, active, create_date, write_date)
            SELECT %s, %s::jsonb, %s, TRUE, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
            WHERE NOT EXISTS (
                SELECT 1 FROM fleet_inspection_vehicle_type WHERE code = %s
            );
        """, (code, json_name, sequence, code))

    # Obtener IDs de los tipos de catálogo
    cr.execute("SELECT code, id FROM fleet_inspection_vehicle_type;")
    type_map = dict(cr.fetchall())
    other_id = type_map.get("other")

    # 3. Verificar si existe la columna legacy 'vehicle_type' en 'fleet_inspection'
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'fleet_inspection' AND column_name = 'vehicle_type'
        );
    """)
    has_legacy_col = cr.fetchone()[0]

    # Verificar si existe la nueva columna 'vehicle_type_id'
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'fleet_inspection' AND column_name = 'vehicle_type_id'
        );
    """)
    has_new_col = cr.fetchone()[0]

    if not has_new_col:
        _logger.warning("Columna 'vehicle_type_id' aún no creada en 'fleet_inspection'.")
        return

    total_migrated = 0

    if has_legacy_col:
        # Migración por lotes mapeando códigos directos (motorcycle, car, truck, other)
        for code, type_id in type_map.items():
            while True:
                cr.execute("""
                    WITH batch AS (
                        SELECT id FROM fleet_inspection
                        WHERE vehicle_type_id IS NULL 
                          AND vehicle_type = %s
                        LIMIT %s
                    )
                    UPDATE fleet_inspection fi
                    SET vehicle_type_id = %s
                    FROM batch
                    WHERE fi.id = batch.id;
                """, (code, BATCH_SIZE, type_id))
                updated = cr.rowcount
                total_migrated += updated
                if updated < BATCH_SIZE:
                    break

        # Cualquier registro restante con tipo no reconocido o nulo -> asignar 'other'
        if other_id:
            while True:
                cr.execute("""
                    WITH batch AS (
                        SELECT id FROM fleet_inspection
                        WHERE vehicle_type_id IS NULL
                        LIMIT %s
                    )
                    UPDATE fleet_inspection fi
                    SET vehicle_type_id = %s
                    FROM batch
                    WHERE fi.id = batch.id;
                """, (BATCH_SIZE, other_id))
                updated = cr.rowcount
                total_migrated += updated
                if updated < BATCH_SIZE:
                    break

    elapsed = time.time() - start_time
    _logger.info(
        "Migración 17.0.2.0.0 completada exitosamente: %d registros procesados en %.3f segundos.",
        total_migrated, elapsed
    )
