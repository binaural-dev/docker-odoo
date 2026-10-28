# Inspecciones de vehículos (`fleet_inspection`)

Módulo escrito originalmente para **Odoo 16**, migrado a **Odoo 18** (Ejercicio 2 de la prueba técnica).

## Qué hace

- Registra inspecciones de los vehículos de Flota con un checklist de puntos (frenos, luces, cauchos…) que se
  carga solo al crear la inspección.
- Estados: borrador → en curso → aprobada / rechazada. Un punto crítico con falla impide aprobar.
- Tipo de vehículo como campo de selección: moto, carro, camión u otro.
- Grupos: *Inspector* (ve solo sus inspecciones) y *Supervisor de inspecciones* (ve todas, aprueba y rechaza).
- Acción planificada diaria que marca las inspecciones con más de 7 días en curso y le crea una actividad al
  inspector.
- Reporte PDF de la inspección.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — migración a Odoo 18 | ✅ Instala en una base nueva, 11/11 pruebas y ninguna advertencia de obsolescencia al instalar |
| B — tipo de vehículo como catálogo + script de migración | ⏳ Pendiente |
| C — script idempotente por lotes, 10.000 registros, MIGRATION_PLAN.md | ⏳ Pendiente |

## Cómo probarlo

```bash
./odoo test prueba-tecnica fleet_inspection -d fleet_prueba
```

Resultado: `0 failed, 0 error(s) of 11 tests`, cobertura 94 %. El registro de la instalación no tiene ninguna
línea `WARNING` ni `ERROR`, y la palabra «deprecat» no aparece.

**Contraprueba** (para demostrar que el registro sí habría mostrado los problemas): se instaló el código de
Odoo 16 tal cual, solo movido a la carpeta de addons y con la versión subida. Odoo 18 mostró:

```
WARNING py.warnings: ... DeprecationWarning: The model odoo.addons.fleet_inspection.models.fleet_inspection is not overriding the create method in batch
WARNING odoo.fields: Field fleet.inspection.vehicle_id: unknown parameter 'states' ...
WARNING odoo.fields: Field fleet.inspection.vehicle_type: unknown parameter 'states' ...
ValueError: Invalid field 'numbercall' on model 'ir.cron'          -> la instalación se detiene
```

Corrigiendo solo el cron, la instalación se detiene en las vistas: `Invalid view type: 'tree'`.

## Tabla de cambios de la migración (16 → 18)

| Qué cambió | Por qué | Cómo lo resolví |
|---|---|---|
| Ubicación del módulo: `src/custom/prueba-tecnica-odoo16/` → `src/custom/prueba-tecnica/` | Estaba fuera del directorio de addons a propósito: con versión `16.0.x` impedía arrancar Odoo 18 | `git mv` para conservar el historial, en el mismo commit que el cambio de versión |
| `version` del manifiesto `16.0.1.0.0` → `18.0.1.0.0` | Odoo solo instala módulos cuya versión empieza con la serie del servidor | Cambio de versión; sin dependencias nuevas (`fleet`, `mail` existen en 18) |
| `@api.model def create(self, vals)` → `@api.model_create_multi def create(self, vals_list)` | Desde la 17, un `create` que no es por lotes genera `DeprecationWarning: ... not overriding the create method in batch` | Recorre `vals_list`; la secuencia se pide por registro y los puntos del checklist se buscan **una sola vez** para todo el lote. Prueba nueva `test_create_batch` |
| `name_get()` → `_compute_display_name()` | `name_get` se eliminó en la 17: Odoo ya no lo llama, así que el nombre «INS/… - placa» habría dejado de mostrarse sin ningún error | `_compute_display_name` con `@api.depends("name", "vehicle_id.license_plate", "vehicle_id.name")`. La prueba pasa a verificar `display_name` |
| Parámetro `states={"draft": [...]}` y `readonly=True` en `vehicle_id` y `vehicle_type` | En la 17+ `states` ya no es un parámetro de campo (`unknown parameter 'states'`) y se ignora: los campos habrían quedado siempre de solo lectura | Se quita del campo y se pone en la vista: `readonly="state != 'draft'"`. Mismo comportamiento que antes: editable solo en borrador |
| `<tree>` → `<list>`, `view_mode` `tree` → `list` | En la 18 la vista de lista se llama `list` (`Invalid view type: 'tree'`) | Renombrado en las 3 listas (inspecciones, checklist interno y puntos) y en las 2 acciones. **Se conservan los XML id** de las vistas para no dejar vistas huérfanas al actualizar |
| `attrs="{'invisible'/'readonly'/'required': [...]}"` | Se eliminó en la 17 (las vistas no cargan) | Expresiones Python: `invisible="not is_overdue"`, `readonly="state in ('approved', 'rejected')"`, `required="state == 'in_progress'"`… con la misma lógica que cada dominio |
| `states="draft"` en botones | Se eliminó en la 17 junto con `attrs` | `invisible="state != 'draft'"` (y `in_progress` / `rejected` en el resto). Los `groups` de los botones se mantienen |
| `invisible="1"` en columnas de listas | En la 17+ `invisible` en una lista oculta la **celda**, no la columna | `column_invisible="True"` para `is_overdue`, `sequence`, `state` y `active` |
| `<div class="oe_chatter">` con 3 campos | En la 18 el chatter es la etiqueta `<chatter/>` | `<chatter/>` |
| `numbercall` y `doall` en `ir.cron` | Se eliminaron de `ir.cron` en la 18 (`Invalid field 'numbercall'`), y la instalación se detenía | Se quitan. En la 18 una acción planificada activa se repite sin límite, igual que `numbercall=-1` |
| `t-esc` en el reporte QWeb | Obsoleto en favor de `t-out` (Odoo avisa con «Found deprecated directive @t-esc») | `t-out`; los `t-field` no cambian. Prueba nueva `test_report_renders` |
| `_("… %s") % valor` | Forma recomendada desde la 17: pasar los argumentos a `_()` para que la traducción se aplique antes de formatear | `_("… %s", valor)` |
| `super(FleetInspection, self)` | Sintaxis de Python 2 | `super()` |
| Pruebas: `from odoo.tests.common import Form` | En la 18 está obsoleto («Since 18.0: odoo.tests.common.Form is deprecated») | `from odoo.tests import Form, TransactionCase, tagged` |
| Pruebas: `name_get()[0][1]` | `name_get` ya no existe | `assertEqual(inspection.display_name, "<número> - AB123CD")` |

**Lo que no cambió** (se revisó y es válido en la 18): `_sql_constraints`, las reglas de registro y
`ir.model.access.csv`, `res.groups` con `users` y `implied_ids`, la categoría
`base.module_category_human_resources_fleet`, los menús bajo `fleet.menu_root` y `fleet.fleet_configuration`,
la secuencia, los datos de los puntos del checklist, `activity_schedule` con `mail.mail_activity_data_todo` y
`groups_id` en las pruebas.

## Supuestos

- Versión declarada: **Odoo 18.0 Community**.
- El comportamiento funcional se mantiene igual que en la 16: no se agregaron funciones, solo se migró.
- El solo lectura de vehículo, tipo y fecha fuera de borrador sigue siendo **de interfaz**, como en la 16 con
  `states`. No se agregó una validación en el servidor porque habría cambiado el comportamiento.

## Limitaciones conocidas

- No se probó una actualización desde una base real en Odoo 16 (migración de datos 16 → 18): eso es una
  migración de base completa (OpenUpgrade o el servicio de Odoo), fuera del alcance del tramo A. El tramo
  probado es instalar en una base nueva de Odoo 18.
- Las vistas se validan al instalar (Odoo rechaza una vista inválida) y el reporte se prueba renderizándolo,
  pero las pantallas no se revisaron una por una en el navegador.
