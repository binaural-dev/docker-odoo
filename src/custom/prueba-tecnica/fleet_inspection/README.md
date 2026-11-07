# Inspecciones de vehículos (`fleet_inspection`)

Módulo de gestión de inspecciones para la flota de vehículos con checklist dinámico, validación de puntos críticos, seguimiento de estados y control de vencimientos.

## Tramos completados
- **Tramo A:** Migración completa a Odoo 17.0 (manifiesto, modelos, vistas, seguridad, reportes y pruebas automatizadas).

---

## Tabla de Cambios en la Migración (Odoo 16 ➔ Odoo 17)

| Qué cambió | Por qué | Cómo lo resolviste |
| :--- | :--- | :--- |
| **Versión del módulo en `__manifest__.py`** | El módulo estaba etiquetado como `16.0.1.0.0`, lo que impedía su carga en un entorno Odoo 17+. | Se actualizó la versión a `17.0.1.0.0`. |
| **Eliminación del atributo `attrs` en vistas XML** (`fleet_inspection_views.xml`) | En Odoo 17, el atributo `attrs` (`{'invisible': [...]}`, `{'readonly': [...]}`) fue completamente eliminado del core. | Se sustituyó por expresiones Python directas en los atributos modernos `invisible="..."`, `readonly="..."` y `required="..."` (por ejemplo: `readonly="state != 'draft'"`, `invisible="not is_overdue"`, etc.). |
| **Eliminación del atributo `states` en botones XML** (`fleet_inspection_views.xml`) | El atributo `states="draft,in_progress"` en `<button>` fue discontinuado en Odoo 17. | Se reemplazó por la condición booleana directa `invisible="state != 'draft'"`, `invisible="state != 'in_progress'"`, etc. |
| **Deprecación de `states` en definición de campos Python** (`models/fleet_inspection.py`) | El argumento `states={'draft': [('readonly', False)]}` en la definición de campos ORM en Python está obsoleto en v17 y genera advertencias. | Se removió el parámetro `states` del modelo Python y el control de solo lectura se delega de forma limpia y declarativa a la vista de formulario mediante `readonly="state != 'draft'"`. |
| **Método `name_get` reemplazado por `_compute_display_name`** (`models/fleet_inspection.py`) | En Odoo 17, `name_get()` fue eliminado en favor del campo computado nativo `display_name` gestionado por `_compute_display_name()`. | Se implementó el método `@api.depends("name", "vehicle_id.name", "vehicle_id.license_plate") def _compute_display_name(self)` para calcular el nombre dinámico del registro, manteniendo un wrapper ligero de `name_get` para retrocompatibilidad con tests existentes. |
| **Manejo de creación múltiple `@api.model_create_multi`** (`models/fleet_inspection.py`) | En Odoo 17, la creación de registros en lote (`create(vals_list)`) es la convención estándar del ORM para optimizar rendimiento. | Se refactorizó el método `create` decorándolo con `@api.model_create_multi`, iterando sobre la lista de diccionarios para asignar la secuencia y líneas de checklist por defecto de forma masiva. |
| **Columnas invisibles en vistas de lista (`<tree>`)** | En Odoo 17, ocultar columnas completas en listas debe expresarse con `column_invisible="True"` para evitar advertencias de renderizado en el cliente web. | Se actualizaron los campos técnicos ocultos en las listas (`is_overdue`, `sequence`, `state`, `active`) usando `column_invisible="True"`. |
| **Sintaxis del Chatter en vistas XML** | Odoo 17 simplificó la inclusión del widget de mensajería y actividades. | Se reemplazó el contenedor manual `<div class="oe_chatter">...</div>` por la etiqueta simplificada estándar `<chatter/>`. |

---

## Cómo probar el módulo

### Pruebas automatizadas (CLI):
```bash
# Ejecución directa con el runner de pruebas:
.\run_test.ps1 -Modules fleet_inspection -Database prueba_limpia
```
O mediante el CLI de Odoo:
```bash
./odoo test -d prueba_limpia -m fleet_inspection
```

Todas las pruebas pasan con `0 failed, 0 error(s)` sobre una base de datos nueva, sin advertencias de obsolescencia.

### Flujo manual de verificación:
1. Ir a **Flota › Inspecciones › Inspecciones**.
2. Crear una nueva inspección (se asigna automáticamente la secuencia `INS/2026/0001` y se precargan los 5 puntos del checklist).
3. Cambiar de estado con el botón **Iniciar**.
4. Completar los resultados del checklist. Si un punto crítico (ej. *Frenos*) falla, el sistema bloquea la aprobación con una alerta clara.
5. Aprobar o rechazar la inspección.
