def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'fleet_inspection' AND column_name = 'vehicle_type';
    """)
    res = cr.fetchone()
    if res and res[0] in ('character varying', 'text'):
        cr.execute("""
            ALTER TABLE fleet_inspection 
            RENAME COLUMN vehicle_type TO vehicle_type_old;
        """)