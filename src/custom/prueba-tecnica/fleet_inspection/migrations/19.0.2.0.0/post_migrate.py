import logging

_logger = logging.getLogger(__name__)

MAPPING = {
    'motorcycle': ('Moto', 10),
    'car': ('Carro', 20),
    'truck': ('Camión', 30),
    'other': ('Otro', 40),
}

def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'fleet_inspection' AND column_name = 'vehicle_type_old';
    """)
    if not cr.fetchone():
        _logger.info("Migración: No se encontró columna 'vehicle_type_old', no se requiere migrar datos.")
        return

    _logger.info("Migración: Asegurando catálogo de tipos de vehículo...")
    type_ids = {}
    for code, (name, seq) in MAPPING.items():
        cr.execute("""
            SELECT id FROM fleet_inspection_vehicle_type WHERE code = %s;
        """, (code,))
        row = cr.fetchone()
        if row:
            type_ids[code] = row[0]
        else:
            cr.execute("""
                INSERT INTO fleet_inspection_vehicle_type (code, name, sequence, active, create_date, write_date)
                VALUES (%s, %s, %s, true, NOW(), NOW())
                RETURNING id;
            """, (code, name, seq))
            type_ids[code] = cr.fetchone()[0]

    _logger.info("Migración: Actualizando inspecciones existentes...")
    for code, type_id in type_ids.items():
        cr.execute("""
            UPDATE fleet_inspection 
            SET vehicle_type_id = %s 
            WHERE vehicle_type_old = %s AND vehicle_type_id IS NULL;
        """, (type_id, code))

    other_id = type_ids.get('other')
    if other_id:
        cr.execute("""
            UPDATE fleet_inspection 
            SET vehicle_type_id = %s 
            WHERE vehicle_type_id IS NULL;
        """, (other_id,))

    _logger.info("Migración completada con éxito. Todos los registros migraron a vehicle_type_id.")