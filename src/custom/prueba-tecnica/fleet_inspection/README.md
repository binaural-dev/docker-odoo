# Fleet Inspection (`fleet_inspection`)

Módulo de control e inspección periódica de flota vehicular, migrado y modernizado desde Odoo 16 hacia **Odoo 19.0**.

## Tramos completados
- **Tramo A:** Migración completa de código Python, datos XML, seguridad, vistas y reportes a la versión 19.0. Eliminación de todas las sintaxis obsoletas (`attrs`, `states`, `tree`, `name_get`, `_sql_constraints`).
- **Tramo B:** Conversión del campo `vehicle_type` de tipo `Selection` a un modelo de catálogo relacional `fleet.inspection.vehicle.type` (Many2one). Implementación de script de migración en `migrations/19.0.2.0.0/` que preserva la información existente sin pérdida de datos, incluyendo la categoría 'Otro'. Prueba automatizada de la migración incluida.

## Tabla de Cambios de Migración (Odoo 16 ➔ Odoo 19)

| Componente | Qué cambió | Por qué (Odoo 19) | Cómo se resolvió |
| :--- | :--- | :--- | :--- |
| **`data/ir_cron_data.xml`** | Se eliminó `<field name="numbercall">-1</field>` y `<field name="doall">False</field>` | Campo eliminado en Odoo 18+; los crons ahora se rigen solo por `active` e intervalos. | Se removió la etiqueta del XML. |
| **`models/fleet_inspection.py`** | `name_get()` reemplazado por `_compute_display_name()` | El método `name_get()` fue eliminado en Odoo 17+. | Se implementó el cómputo del campo `display_name` combinando secuencia y placa. |
| **`models/fleet_inspection.py`** | `create()` unitario a multi-registro | Odoo 17+ exige soporte nativo de creación por lotes (`vals_list`). | Se agregó `@api.model_create_multi`, iterando `vals_list` y usando `fields.Command.create()`. |
| **`models/fleet_inspection.py`** | Eliminación de `states={...}` en campos | El atributo `states` en definiciones Python está deprecado y bloquea migraciones. | Se eliminó del modelo Python; la reactividad se delegó a la vista XML (`readonly="state != 'draft'"`). |
| **`models/fleet_inspection.py`** | `_sql_constraints` reemplazado | La lista de tuplas `_sql_constraints` fue removida en Odoo 19. | Se implementó el descriptor `_name_uniq = models.Constraint('unique(name)', ...)`. |
| **`security/fleet_inspection_security.xml`** | `category_id` eliminado de `res.groups` | Odoo 19 desacopló las categorías de grupos introduciendo el modelo `res.groups.privilege`. | Se declaró un registro `res.groups.privilege` y se asoció con `privilege_id`. |
| **`security/fleet_inspection_security.xml`** | `users` renombrado a `user_ids` | Estandarización de nombres relacionales Many2many en Odoo 19. | Se actualizó el campo en la asignación del grupo supervisor. |
| **Vistas XML** | `<tree>` sustituido por `<list>` | La etiqueta `<tree>` está en desuso y eliminada en Odoo 18+. | Se migraron todas las vistas de lista a `<list>` y los `view_mode` a `list,form`. |
| **Vistas XML** | `attrs="..."` y `states="..."` | Sintaxis eliminada en Odoo 17+. | Se reemplazaron por `invisible="condicion"`, `readonly="condicion"` y `required="condicion"`. |
| **Modelo de datos** | `vehicle_type` de Selection a Many2one | Requerimiento de catálogo configurable por el usuario. | Se creó el modelo `fleet.inspection.vehicle.type` y se escribió la migración SQL segura. |

## Estrategia de Migración de Datos (`migrations/19.0.2.0.0/`)
Para actualizar bases de datos con datos previos sin error de colisión de tipos (PostgreSQL no permite convertir directamente de `varchar` a `integer` de llave foránea):
1. **`pre-migrate.py`:** Detecta si la columna `vehicle_type` existe como `varchar` y la renombra a `vehicle_type_old`.
2. **ORM Auto-Init:** Odoo crea la tabla del nuevo catálogo `fleet_inspection_vehicle_type` y la nueva columna entera `vehicle_type_id`.
3. **`post-migrate.py`:** 
   * Asegura la creación idempotente de los 4 tipos base (`motorcycle`, `car`, `truck`, `other`).
   * Ejecuta un `UPDATE` masivo por lotes vinculando cada inspección con el ID que corresponde a su valor antiguo.
   * Cualquier valor imprevisto o nulo se asigna de manera segura a `'other'`.

## Cómo Probar el Módulo
Correr las pruebas unitarias y de migración:
```bash
./odoo test prueba_v19 fleet_inspection