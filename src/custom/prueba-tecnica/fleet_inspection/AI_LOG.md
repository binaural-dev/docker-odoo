# AI Log — `fleet_inspection`

Registro del uso de herramientas de Inteligencia Artificial durante el desarrollo y migración del módulo.

## Tramo A — Migración a Odoo 17.0

### Herramienta utilizada
- Antigravity / LLM Asistente de Desarrollo Odoo.

### Prompts y consultas principales
- Diagnóstico de incompatibilidades entre Odoo 16 y Odoo 17 (eliminación de `attrs` y `states` en vistas, deprecación de `name_get` a favor de `_compute_display_name`, sintaxis moderna de `<chatter/>`).
- Adaptación de `@api.model_create_multi` para optimizar creación masiva de registros y checklist.
- Generación de la tabla comparativa técnica para el `README.md`.

### Decisiones tomadas por el desarrollador
- Se mantuvo un método `name_get()` como capa de compatibilidad para asegurar que llamadas externas o tests legados no rompan, mientras se implementó `_compute_display_name()` como estándar v17.
- Se trasladó la lógica de sólo lectura (`readonly`) de los campos `vehicle_id` y `vehicle_type` de Python a la vista de formulario XML con `readonly="state != 'draft'"`, eliminando las advertencias de desuso del argumento `states` en Python.
- Se aplicó `column_invisible="True"` en las columnas auxiliares de listas (`<tree>`) según las buenas prácticas de Odoo 17.

### Validación y pruebas
- Pruebas unitarias ejecutadas con base de datos limpia pasando 9/9 tests sin fallos ni warnings.

---

## Tramo B — Conversión a Catálogo y Script de Migración

### Prompts y consultas principales
- Estrategia de migración de columna `Selection` a `Many2one` en Odoo 17 sin pérdida de datos.
- Manejo de campos `translate=True` en inserciones directas PostgreSQL (`jsonb`).
- Diseño de prueba automatizada para testear la función `migrate()`.

### Decisiones tomadas por el desarrollador
- Se creó el modelo `fleet.inspection.vehicle.type` con constraint único sobre el campo `code`.
- Se introdujo `vehicle_type_id` como `Many2one` y se conservó `vehicle_type` como campo relacionado a `vehicle_type_id.code` con fallback en `create()` y `write()` para preservar compatibilidad con llamadas existentes.
- Se escribió el script `migrations/17.0.2.0.0/post-migrate.py` que asegura los registros base en catálogo y transfiere los datos legacy por lotes.
- Se creó la prueba `TestFleetInspectionMigration` para certificar la integridad de los datos y la preservación de la categoría `'other'`.

---

## Tramo C — Idempotencia, Procesamiento Masivo y Plan de Migración

### Prompts y consultas principales
- Optimización de script SQL para soportar 10.000 registros mediante bloques CTE con `LIMIT %s` (`BATCH_SIZE = 2000`).
- Medición de rendimiento real y elaboración del documento `MIGRATION_PLAN.md` para clientes corporativos.

### Decisiones tomadas por el desarrollador
- Se utilizó una consulta CTE con subquery `LIMIT %s` en PostgreSQL para procesar 10.000 registros en lotes de 2.000, evitando saturar la memoria o bloquear tablas extensamente.
- Se ejecutó benchmark real con 10.000 registros sintéticos medidos en base de datos: 0.148 segundos de ejecución y 0.011 segundos en la prueba de idempotencia.
- Se estructuró un plan de reversión (*rollback*) paso a paso y protocolos de pre/post verificación.
