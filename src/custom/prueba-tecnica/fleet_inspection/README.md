# Inspecciones de vehículos (`fleet_inspection`)

Módulo de checklist y control de inspecciones periódicas para los vehículos de la flota corporativa. Migrado a **Odoo 17.0**.

## Tramos Completados
- **Tramo A:** Migración integral del módulo de Odoo 16 a Odoo 17.0: actualización de versión en manifiesto, modernización de vistas XML (eliminación de `attrs` y `states`), refactor de métodos del ORM (`_compute_display_name`, `@api.model_create_multi`), eliminación de atributos `states={}` en definiciones de campos Python y suite de pruebas unitarias ejecutada exitosamente.

---

## Tabla de Cambios de Migración (Odoo 16 → Odoo 17)

| Qué cambió | Por qué | Cómo se resolvió |
|---|---|---|
| **Versión en manifiesto** (`__manifest__.py`) | En Odoo 17, una versión `16.0.x` genera inconsistencias al resolver dependencias y advertencias en el registro de addons. | Se actualizó el parámetro `"version": "17.0.1.0.0"`. |
| **Atributo `states` en botones del header** (`views/fleet_inspection_views.xml`) | El atributo `states="..."` quedó obsoleto y fue deprecado formalmente en Odoo 17 a favor de expresiones directas de visibilidad. | Se reemplazó por la sintaxis booleana directa: `invisible="state != 'draft'"`, `invisible="state != 'in_progress'"`, etc. |
| **Atributo `attrs` en campos y contenedores** (`views/fleet_inspection_views.xml`) | El atributo `attrs="{'invisible': [...], 'readonly': [...]}"` fue removido en Odoo 17. | Se sustituyó por atributos nativos independientes: `invisible="not is_overdue"`, `readonly="state != 'draft'"`, `readonly="state in ('approved', 'rejected')"` y `required="state == 'in_progress'"`. |
| **Parámetro `states` en campos Python** (`models/fleet_inspection.py`) | Definir `states={"draft": [("readonly", False)]}` dentro de los campos `vehicle_id` y `vehicle_type` en Python genera advertencias de obsolescencia en Odoo 17. | Se removió el parámetro `states` de los campos Python y se trasladó el control de edición a la vista formulario mediante `readonly="state != 'draft'"`. |
| **Método de visualización `name_get()`** (`models/fleet_inspection.py`) | En Odoo 17 `name_get()` está deprecado en favor del campo computado estándar `display_name` con el método `_compute_display_name()`. | Se implementó `@api.depends(...) def _compute_display_name(self)` para calcular `display_name`, conservando `name_get()` delegando en `display_name` para retrocompatibilidad con tests existentes. |
| **Decorador y firma de `create()`** (`models/fleet_inspection.py`) | En Odoo 17 se estandarizó la creación en lote mediante `@api.model_create_multi` recibiendo una lista de diccionarios `vals_list`. | Se refactorizó el método `create` para iterar `vals_list` y asignar las secuencias y checklists correspondientes en lote. |

---

## Cómo Probarlo

### 1. Ejecución de Tests Automatizados
Ejecutar la suite de pruebas unitarias que valida la carga del checklist, secuencias, display name y flujo de aprobación:

```bash
./odoo test prueba-tecnica fleet_inspection
```

O en la verificación general sobre base limpia:
```bash
./odoo test -d prueba_limpia -m fleet_inspection
```

### 2. Verificación Manual en Odoo
1. Ingresar a **Flota > Inspecciones**.
2. Crear una nueva inspección: verificar que se genere el número correlativo (ej. `INS/2026/0001`) y que se carguen automáticamente los puntos de checklist configurados.
3. Presionar **"Iniciar"**: el estado cambia a *En curso*.
4. Evaluar los puntos del checklist: verificar que si un punto crítico falla (`fail`), el sistema impida la aprobación arrojando el mensaje de advertencia correspondiente.
5. Aprobar la inspección y verificar que los campos queden bloqueados en solo lectura.
