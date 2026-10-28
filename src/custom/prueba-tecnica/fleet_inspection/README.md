# Inspecciones de vehículos (`fleet_inspection`)

Módulo escrito originalmente para **Odoo 16**, migrado a **Odoo 18** (Ejercicio 2 de la prueba técnica).

## Qué hace

- Registra inspecciones de los vehículos de Flota con un checklist de puntos (frenos, luces, cauchos…) que se
  carga solo al crear la inspección.
- Estados: borrador → en curso → aprobada / rechazada. Un punto crítico con falla impide aprobar.
- Tipo de vehículo como **catálogo** (`fleet.inspection.vehicle.type`): moto, carro, camión y otro vienen de
  fábrica, y el supervisor puede agregar más en *Flota › Configuración › Tipos de vehículo (inspecciones)*.
  Hasta la versión 18.0.1.0.0 era un campo de selección (ver «Tramo B»).
- Grupos: *Inspector* (ve solo sus inspecciones) y *Supervisor de inspecciones* (ve todas, aprueba y rechaza).
- Acción planificada diaria que marca las inspecciones con más de 7 días en curso y le crea una actividad al
  inspector.
- Reporte PDF de la inspección.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — migración a Odoo 18 | ✅ Instala en una base nueva, sin advertencias de obsolescencia |
| B — tipo de vehículo como catálogo + script en `migrations/` | ✅ Probado con una prueba de la lógica y con una actualización real con `-u` (sección «Tramo B») |
| C — script idempotente por lotes, 10.000 inspecciones medidas, MIGRATION_PLAN.md | ✅ Lotes de 1.000 con paginación por id; 10.000 en ~0,5 s de script (~4,6 s el `-u`) y 100.000 en ~5 s, con memoria constante (133 MB); plan con reversión ensayada. Ver [MIGRATION_PLAN.md](MIGRATION_PLAN.md) |

## Cómo probarlo

```bash
./odoo test prueba-tecnica fleet_inspection -d fleet_prueba
```

Resultado: `0 failed, 0 error(s) of 18 tests`, cobertura 96 % (100 % en `migration_utils.py`). El registro
de la instalación no tiene ninguna línea `WARNING` ni `ERROR`, y la palabra «deprecat» no aparece. La única
advertencia del registro de las pruebas es la que provoca a propósito la prueba de un valor fuera del
catálogo («valor «trailer» fuera del catálogo; se creó como tipo nuevo»).

## Tramo B — tipo de vehículo como catálogo

### Qué cambia (versión 18.0.1.0.0 → 18.0.1.1.0)

- Modelo nuevo `fleet.inspection.vehicle.type` (nombre traducible, código único, secuencia, activo). Los 4
  tipos iniciales vienen en datos y su **código es el valor de la antigua selección** (`motorcycle`, `car`,
  `truck`, `other`). Eso es lo que permite relacionarlos al migrar.
- `fleet.inspection.vehicle_type` (selección) se reemplaza por `vehicle_type_id` (many2one, obligatorio, por
  defecto «Carro» como antes, `ondelete="restrict"` para que no se pueda borrar un tipo en uso). Se cambia en
  vistas, búsqueda (agrupar por tipo) y reporte.
- Lectura del catálogo para inspectores; alta y edición para supervisores.

### Script de migración

`migrations/18.0.1.1.0/` llama a funciones de `migration_utils.py`, separadas para poder probarlas:

| Paso | Cuándo corre | Qué hace |
|---|---|---|
| `pre-migrate.py` → `save_legacy_vehicle_type` | Antes de cargar el modelo nuevo | Copia `vehicle_type` a una columna propia, `legacy_vehicle_type`. Hace falta porque, al terminar la actualización, **Odoo borra la columna de un campo que ya no está en el modelo**. La copia sobrevive y sirve para verificar y para revertir |
| `post-migrate.py` → `assign_vehicle_types` | Con el catálogo ya cargado | `vehicle_type_id` = el tipo cuyo `code` es el valor respaldado. Si aparece un valor que no está en el catálogo, **lo crea como tipo nuevo** en lugar de perderlo o convertirlo en «otro». Al final verifica que ninguna inspección quede sin tipo; si queda alguna, **aborta la actualización** (Odoo deshace todo) |

Ambas funciones son **idempotentes**: solo respaldan filas sin respaldo y solo asignan tipo a inspecciones
que no lo tienen. Por eso tampoco pisan una corrección hecha a mano.

### Cómo se probó

**1. Prueba de la lógica** (`tests/test_vehicle_type_migration.py`). Dentro de la transacción de la prueba
simula la tabla de la 18.0.1.0.0 (columna de selección con valores y many2one vacío) y verifica:

| Prueba | Qué demuestra |
|---|---|
| `test_every_inspection_keeps_its_type` | Moto, carro, camión y **otro** quedan con su tipo del catálogo (sin duplicarlo); un valor desconocido se crea como tipo y ninguna inspección queda sin tipo |
| `test_small_batches_give_the_same_result` | (C) Con lotes de 2 filas, 3 lotes por paso y el mismo resultado |
| `test_resumes_after_a_partial_run` | (C) Si una corrida quedó a medias, la siguiente completa solo lo que faltaba |
| `test_running_twice_changes_nothing` | Correr pre y post otra vez no respalda ni asigna nada ni crea tipos |
| `test_rerun_does_not_overwrite_manual_corrections` | Una corrección manual posterior se respeta |
| `test_aborts_if_an_inspection_would_stay_without_type` | Si una inspección quedaría sin tipo, la migración aborta |
| `test_fresh_install_has_nothing_to_migrate` | En una base nueva los scripts no hacen nada |

**2. Actualización real con `-u`**, el escenario que pide el enunciado:

1. Base `fleet_upg` con la versión del tramo A (18.0.1.0.0) y 26 inspecciones: 7 moto, 11 carro, 5 camión y
   3 otro.
2. Código del tramo B (manifiesto 18.0.1.1.0) y
   `odoo -d fleet_upg -u fleet_inspection --stop-after-init`.
3. Resultado:

```
module fleet_inspection: Running upgrade [>18.0.1.1.0] pre-migrate
fleet_inspection: 26 inspecciones respaldadas en legacy_vehicle_type
module fleet_inspection: Running upgrade [18.0.1.1.0>] post-migrate
fleet_inspection: 26 inspecciones con tipo asignado; tipos creados: ninguno
```

| Verificación después de actualizar | Resultado |
|---|---|
| Versión instalada | 18.0.1.1.0 |
| Inspecciones por tipo | car (Carro) 11 · motorcycle (Moto) 7 · other (Otro) 3 · truck (Camión) 5, igual que antes |
| Inspecciones sin tipo | 0 |
| Inspecciones con un tipo distinto al valor respaldado | 0 |
| `vehicle_type_id` con `NOT NULL` en la base | Sí |
| Columnas | `vehicle_type` eliminada por Odoo; quedan `vehicle_type_id` y `legacy_vehicle_type` (respaldo) |
| Segunda corrida de pre y post sobre esa base | 0 respaldadas, 0 asignadas, ningún cambio |

## Tramo C — por lotes, 10.000 inspecciones y plan de producción

- **Lotes:** cada paso procesa 1.000 inspecciones por sentencia, recorriendo la tabla por id desde el último
  lote. Solo los ids del lote pasan por Python, así que la memoria no depende del volumen. El avance queda en
  el registro (`respaldo: lote 7, 1000 filas (acumulado 7000, 0.07 s)`).
- **Idempotente:** cada paso toca solo lo pendiente. Correrlo dos veces, o retomarlo después de una corrida a
  medias, deja el mismo resultado (pruebas `test_running_twice_changes_nothing` y
  `test_resumes_after_a_partial_run`).
- **Datos de prueba:** [`scripts/generate_inspections.py`](scripts/generate_inspections.py) genera
  inspecciones con el ORM (con su checklist), con semilla fija, más 10 con un valor fuera del catálogo.
- **Medido, no supuesto** (detalle en [MIGRATION_PLAN.md](MIGRATION_PLAN.md#mediciones)):

| Inspecciones | `-u` completo | Respaldo | Asignación | Memoria máx. |
|---|---|---|---|---|
| 10.000 (3 corridas) | 4,50–4,66 s | 0,10–0,11 s | 0,38–0,43 s | 133 MB |
| 100.000 (2 corridas) | 9,46–9,64 s | 1,17–1,19 s | 3,95–4,16 s | 133–134 MB |

- **[MIGRATION_PLAN.md](MIGRATION_PLAN.md):** respaldo, verificación previa con criterios para seguir o no,
  ejecución, verificación posterior (SQL y en la interfaz) y reversión en dos casos: antes o después de que
  los usuarios vuelvan a trabajar. La reversión del segundo caso se ensayó sobre una copia migrada.

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
