"""Genera inspecciones de prueba para medir la migración del tipo de vehículo. Solo en bases de PRUEBA.

Uso (sobre una base con fleet_inspection 18.0.1.0.0, la de selección):
    TOTAL=10000 odoo shell -c <odoo.conf> -d <base> --no-http < generate_inspections.py

- Crea las inspecciones con el ORM (con su checklist), en lotes de 1.000, con una semilla fija para que la
  distribución de tipos sea siempre la misma.
- Desactiva el seguimiento del chatter (tracking_disable) solo para acelerar la carga de datos de prueba.
- Agrega 10 inspecciones con un valor fuera del catálogo («trailer») vía SQL, porque el ORM no deja guardar un
  valor que no está en la selección: simula datos heredados o personalizados.
"""
import os
import random
import time

total = int(os.environ.get("TOTAL", "10000"))
batch_size = 1000
rng = random.Random(2026)
types = ["motorcycle", "car", "truck", "other"]
weights = [25, 45, 20, 10]

Inspection = env["fleet.inspection"].with_context(tracking_disable=True, mail_create_nolog=True)
brand = env["fleet.vehicle.model.brand"].create({"name": "Marca carga"})
model = env["fleet.vehicle.model"].create({"name": "Modelo carga", "brand_id": brand.id})
vehicles = env["fleet.vehicle"].create(
    [{"model_id": model.id, "license_plate": f"CARGA{i:03d}"} for i in range(50)]
)

start = time.perf_counter()
created = 0
while created < total:
    size = min(batch_size, total - created)
    Inspection.create([
        {"vehicle_id": rng.choice(vehicles).id, "vehicle_type": rng.choices(types, weights)[0]}
        for _ in range(size)
    ])
    env.cr.commit()
    env.invalidate_all()
    created += size
    print(f"GEN {created}/{total} en {time.perf_counter() - start:.1f} s", flush=True)

env.cr.execute("""
    UPDATE fleet_inspection SET vehicle_type = 'trailer'
     WHERE id IN (SELECT id FROM fleet_inspection ORDER BY id DESC LIMIT 10)
""")
env.cr.commit()
print(f"GEN listo: {total} inspecciones en {time.perf_counter() - start:.1f} s (10 con «trailer»)", flush=True)
