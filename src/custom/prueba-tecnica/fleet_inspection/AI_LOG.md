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
