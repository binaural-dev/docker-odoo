---

### `src/custom/fleet_inspection/AI_LOG.md`

```markdown
# AI_LOG — fleet_inspection

## Herramientas
- Gemini 3.8 Flash - AI Studio

## Prompts clave
1. *Identificar elementos obsoletos entre Odoo 16 y Odoo 19 en modelos con checklist, campos calculados y acciones planificadas.*
   - Se identificaron la necesidad de remover `numbercall`, migrar `name_get` y actualizar vistas `<tree>` a `<list>`.
2. *Estrategia de script de migración SQL en Odoo para convertir un campo Selection varchar a Many2one sin tiempo de caída ni errores de casteo.*
   - Se diseñó el esquema de dos fases (`pre-migrate` renombrando columna y `post-migrate` poblando y actualizando IDs).
3. *Cómo adaptar reglas de seguridad y res.groups en Odoo 19.*
   - Se detectó el error al importar `category_id` y se introdujo `res.groups.privilege`.

## Lo que la IA hizo mal
1. **Persistencia con `_sql_constraints`:** Inicialmente conservó `_sql_constraints = [('name_uniq', ...)]`, sin advertir que en Odoo 19 este mecanismo fue sustituido por `models.Constraint()`.
2. **Definición de grupos de seguridad:** La IA asumió que `res.groups` mantenía el campo `category_id` y el campo `users`. En Odoo 19 esto provocó una excepción crítica al iniciar la base de datos (`ValueError: Invalid field 'category_id' in 'res.groups'`).
3. **Omisión del campo requerido en los tests del Many2one:** Al migrar a `vehicle_type_id`, omitió que el campo es requerido lo que rompió el helper `Form` en las pruebas unitarias.
4. **Vistas search:** Al migrar las vistas search, la IA agrega string en el group_by, lo cual causa error de pantalla rosada al instalar.
## Lo que escribiste tú sin IA
- La lógica de testeo de migración `test_migration_vehicle_type_logic` usando transacciones SQL directas para validar que ninguna inspección quede huérfana.
- Mapeo de vistas para la administración de tipos de vehículos en el menú de Flota.
