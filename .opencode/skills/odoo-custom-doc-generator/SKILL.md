# Generate Custom Module Documentation

Genera un informe estructurado de todas las personalizaciones Odoo de un proyecto, detallando qué flujos de negocio modifican, qué hace cada módulo y cómo validarlo. El informe está pensado para entregárselo a un consultor funcional, no a un desarrollador.

## Trigger

Cargar esta skill cuando el usuario pida:
- "genera un informe de personalizaciones"
- "genera un informe de personalizaciones para [proyecto]"
- "qué flujos tocan los custom"
- "guía para el consultor" + contexto de módulos
- "documentación de módulos custom"
- "cómo validar los módulos"
- "informe de customizaciones"

**Si el usuario NO especifica el proyecto**, auto-detectarlo usando la Fase 1 (buscar prefijo desde el working directory). Solo preguntar si no se puede detectar automáticamente.

## Fase 1 — Descubrir el proyecto

### 1.1 Encontrar la raíz del workspace

El usuario puede estar en cualquier profundidad del proyecto. Buscar hacia arriba desde el working directory actual hasta encontrar una carpeta que contenga subdirectorios con `__manifest__.py`. Esa es la raíz de módulos custom.

Si no se encuentra automáticamente, preguntar al usuario: "¿En qué directorio están los módulos custom?"

### 1.2 Detectar el prefijo del proyecto

Listar todas las carpetas que contengan `__manifest__.py` en la raíz de módulos custom. Extraer el prefijo común. Ejemplos:
- `bambary_invoice`, `bambary_sale`, `bambary_stock` → prefijo = `bambary`
- `farmatodo_invoice`, `farmatodo_product` → prefijo = `farmatodo`

Regla: el prefijo es la parte antes del primer `_` que se repite en ≥2 módulos.
Si solo hay 1 módulo o todos los módulos tienen prefijos distintos, preguntar al usuario.

### 1.3 Filtrar solo módulos del proyecto

Excluir carpetas que NO sean módulos custom del proyecto:
- `integra_addons/`
- `third-party-addons/`
- `odoo-venezuela/`
- `enterprise/`
- `design-themes/`
- Cualquier carpeta que no empiece con el prefijo detectado
- Carpetas que empiezan con `.` (`.git`, `.opencode`)
- `__pycache__/`

De las restantes, conservar solo las que tengan `__manifest__.py` **y** `installable: True` (o sin ese key, que por defecto es True).

### 1.4 Determinar nombre del proyecto

Usar el prefijo detectado. Si el prefijo es `bambary`, el nombre del proyecto es "Bambary". Si es `farmatodo`, es "Farmatodo". Preguntar al usuario si hay ambigüedad.

## Fase 2 — Analizar cada módulo

Para cada módulo, inspeccionar en orden:

### 2.1 `__manifest__.py`

Extraer:
- `name` — nombre display del módulo
- `summary` — descripción corta (si no hay, usar `name`)
- `version` — versión (útil para identificar cambios recientes)
- `depends` — módulos Odoo de los que depende. **Importante**: las dependencias revelan qué flujos toca. `sale` → ventas, `account` → facturación, `stock` → inventario, `purchase` → compras, `hr` → RRHH
- `data` — archivos de datos que carga. Separar por tipo (security, views, data, report)
- `installable` — si es False, saltar el módulo
- `auto_install` — si es True, anotarlo (se instala solo bajo ciertas condiciones)
- `application` — si es True, es una aplicación principal

### 2.2 Modelos (`models/`)

Para cada archivo `.py` en `models/`, identificar:
- **Herencia**: `_inherit = "model.name"` → modifica modelo existente. `_name = "new.model"` → crea modelo nuevo
- **Campos nuevos**: nombre, tipo, propósito (inferido del nombre y del código circundante)
- **Métodos nuevos**: nombre y qué hace (inferido del cuerpo del método — decorators `@api.depends`, `@api.onchange`, `@api.model`, llamadas a ORM, etc.)
- **Métodos sobreescritos**: métodos que ya existen en Odoo estándar y están siendo extendidos con `super()`

Si el archivo solo tiene `_inherit` y no agrega campos/métodos, marcarlo como "herencia vacía — posible extensión futura".

### 2.3 Vistas (`views/`)

Para cada archivo `.xml` en `views/`:
- `inherit_id` o `expr` → ¿qué vista Odoo modifica?
- ¿Qué agrega, oculta o modifica? (campos, botones, tabs, filters, árboles, kanban)
- Si no tiene `inherit_id`, es una vista nueva (para un modelo nuevo)

### 2.4 Reportes (`report/`)

Para cada archivo `.xml` en `report/`:
- `id="action_*"` o `<record model="ir.actions.report">` → acción de reporte
- `template id="*"` → plantilla QWeb
- `report_name` y `report_file` → nombre técnico
- Modelo asociado
- Moneda relevante: `o.currency_id.symbol` (base), `o.foreign_currency_id.symbol` (alterna), ambos (multimoneda)

### 2.5 Seguridad (`security/`)

- `ir.model.access.csv`: modelos + permisos (crear, leer, escribir, borrar)
- `res.groups`: grupos definidos (id, name, implied_ids, category_id)
- `ir.rule`: reglas de registro (domain_force — usualmente multi-compañía)

### 2.6 Datos (`data/`)

- Datos precargados: `ir.actions.server`, `ir.cron`, `ir.config_parameter`, secuencias, templates de email, etc.

### 2.7 Wizards (`wizard/`)

- Modelos transient (`_transient` en el modelo o `models.TransientModel`)
- Vistas de wizard
- ¿Qué flujo inicia? (ej: facturar desde SO, crear pago, etc.)

### 2.8 Controladores (`controllers/`)

Si existe la carpeta:
- Rutas HTTP definidas (`@http.route`)
- ¿Son portal, API, webhook, o reporte?
- Autenticación requerida (`auth='user'`, `auth='public'`)

### 2.9 Hooks (`hooks.py`, `__init__.py`)

- `pre_init_hook` / `post_init_hook` → qué hace (ej: llenar datos iniciales, migrar)
- `uninstall_hook` → limpieza al desinstalar

### 2.10 Assets estáticos (`static/`)

Si existe, anotar si hay CSS/JS personalizado que afecte la UI. No es necesario detallar cada archivo, solo indicar "incluye assets estáticos que modifican la interfaz".

## Fase 3 — Mapear flujos Odoo afectados

Usar esta tabla para clasificar cada modelo intervenido:

| Flujo Odoo | Modelos clave |
|------------|--------------|
| Ventas | `sale.order`, `sale.order.line`, `sale.order.template` |
| Facturación / Contabilidad | `account.move`, `account.move.line`, `account.payment`, `account.tax`, `account.account`, `account.journal` |
| Retenciones | `account.retention`, `account.retention.line` |
| Productos | `product.template`, `product.product`, `product.packaging`, `product.supplierinfo` |
| Inventario / Almacén | `stock.move`, `stock.move.line`, `stock.picking`, `stock.quant`, `stock.lot`, `stock.warehouse`, `stock.location` |
| Compras | `purchase.order`, `purchase.order.line` |
| Distribución / Guías | `stock.picking.distribution` |
| Punto de Venta (POS) | `pos.order`, `pos.order.line`, `pos.session`, `pos.config` |
| Contactos (CRM base) | `res.partner`, `res.company`, `res.users` |
| Configuración | `res.config.settings` |
| Portal / Website | Cualquier `@http.route` con `auth='public'`, `website.*`, `portal.*` |
| eCommerce | `sale.order` con `website_id`, `website.sale.order` |
| Manufactura (MRP) | `mrp.production`, `mrp.bom`, `mrp.workorder` |
| RRHH / Empleados | `hr.employee`, `hr.contract`, `hr.department` |
| Nómina | `hr.payslip`, `hr.salary.rule` |
| Proyectos | `project.project`, `project.task` |
| Mantenimiento | `maintenance.request` |
| Helpdesk | `helpdesk.ticket` |
| Reportes | Templates QWeb en `report/` |
| Seguridad | `res.groups`, `ir.model.access`, `ir.rule` |

Si un módulo tiene `depends: ["sale", "stock"]` y modelo `sale.order`, asignarlo a **Ventas** y a **Inventario** si también modifica `stock.*`.

Si un módulo solo crea vistas o reportes sin tocar modelos, clasificarlo según el modelo del reporte/vista.

## Fase 4 — Detectar bugs y patrones sospechosos

Durante el análisis, buscar estos patrones comunes:

- `t-if="use_agrupation_lines"` sin prefijo `o.` → variable no existente en QWeb
- Hardcodeo de keys de diccionario cuando hay una variable calculada (`tax_totals['groups_by_subtotal']` vs `tax_totals[group_key]`)
- `t-foreach` sin `t-as` → error de render
- `t-field` vs `t-out` mal usado (t-field requiere campo, t-out requiere expresión)
- `_inherit` sin `_name` en modelo nuevo → puede heredar registro equivocado
- `compute` sin `store=True` cuando se usa en vistas/search
- `related` sin `readonly=False` cuando el usuario necesita editarlo
- `@api.onchange` que no retorna warning/domain cuando la validación falla (el usuario no ve el error)
- Templates QWeb con wrappers muertos al final (otro `<template>` que nunca se llama)
- `installable: False` → módulo en desarrollo, no incluir
- `auto_install: True` → se instala automático, probar que las dependencias lo activen
- Módulos sin `__manifest__.py` → no son módulos, ignorar

## Formato de salida

Estructura exacta del informe:

```
# INFORME DE PERSONALIZACIONES [NOMBRE PROYECTO] (GUÍA PARA EL CONSULTOR)

Este documento resume los [N] módulos personalizados que modifican los flujos
de [áreas principales] en Odoo.

## RESUMEN DE FLUJOS Y MÓDULOS ASOCIADOS

| Flujo | Módulos que lo modifican |
|-------|-------------------------|
| Ventas (Sale Order) | módulo1, módulo2 |
| Facturación (Invoice) | módulo3, módulo4 |
| ... | ... |

## DETALLE POR MÓDULO: QUÉ HACE Y CÓMO VALIDARLO

### N. nombre_módulo (Título descriptivo)

**Depende de:** [módulos Odoo estándar + custom]

**Qué hace:** [1-2 párrafos explicando el propósito de negocio, no técnico]

**¿Qué toca?:**
- [Modelo Odoo afectado]: [qué campo/feature agrega]. [restricción o comportamiento especial].
- ...

**¿Cómo validar?:**
- [Instrucción paso a paso en lenguaje de consultor, no de desarrollador]
- ...

---

[repetir por cada módulo]

## BUGS CONOCIDOS

⚠️ **[archivo:línea]** — [descripción del bug]. [impacto]. [sugerencia de fix].

## ORDEN DE PRUEBAS RECOMENDADO

[Lista numerada indicando qué módulos/flujos probar primero, basado en dependencias:
los módulos sin dependencias custom primero, luego los que dependen de otros custom]
```

### Reglas de redacción

- **NO usar terminología de código** (QWeb, `_inherit`, `super()`, ORM). El informe es para un consultor
- **Sí mencionar nombres de campos Odoo** (partner, SO, picking) porque el consultor los conoce
- **Paso a paso accionable**: "Ir a Ventas → Clientes → seleccionar cliente → pestaña X → activar toggle Y"
- **Una línea por cada campo/feature** en "¿Qué toca?"
- **Un bullet por paso de validación** en "¿Cómo validar?"
- **Inferir propósito de negocio**, no describir implementación técnica
- Si un campo se llama `is_fiscal`, asumir que "controla si la orden incluye impuestos" sin necesidad de leer TODO el código

### Ejemplo de entrada de módulo

```
### 1. bambary_agrupation (Agrupación de Líneas)

**Depende de:** `sale`, `account`, `product`, `binaural_invoice`, `binaural_sale`

**Qué hace:** Permite agrupar líneas de producto en ventas y facturas por un código
de agrupación. En lugar de mostrar cada producto por separado, los productos con el
mismo código se consolidan en una sola línea combinada (cantidad = suma, precio
promedio, subtotal = suma). Útil para simplificar facturas con muchos ítems similares.

**¿Qué toca?:**
- Partner (Cliente): Nuevo toggle "Invoicing with grouping". Si está activo, las líneas
  se agrupan al vender/facturar.
- Producto: Nuevo campo "Código de agrupación". Si el producto ya pertenece a un grupo,
  no se permite cambiar su precio ni impuestos desde la ficha (debe hacerse desde el grupo).
- Orden de Venta: Las líneas se agrupan automáticamente al validar si el cliente tiene
  el toggle activo.
- Factura: Mismo comportamiento — las líneas de factura se agrupan según el código.
- Compañía: Nueva configuración para activar/desactivar la funcionalidad globalmente
  y definir cuántas líneas agrupadas máximo se permiten.
- Nuevo menú "Códigos de Agrupación" donde se administran los grupos (código, marca,
  país de origen, empaque, precio, impuestos).

**¿Cómo validar?:**
- Ir a Ajustes → activar "Invoicing with grouping" en la compañía
- Ir al nuevo menú "Códigos de Agrupación" y crear un código con precio e impuestos
- Asignar ese código a 2 o más productos desde la ficha de cada uno
- Verificar que al intentar cambiar el precio de un producto agrupado, el sistema lo bloquea
- Ir a un cliente, activar el toggle "Invoicing with grouping"
- Crear una orden de venta para ese cliente con los productos del grupo
- Validar la orden → las líneas deben aparecer agrupadas en una sola
- Crear la factura desde la orden → debe mantener la agrupación
- Cambiar el precio desde el grupo → verificar que se actualiza en todos los productos
- Probar con un cliente que NO tenga el toggle activo → líneas deben verse normalmente
```

## Fase 5 — Clasificar por dependencia y orden de prueba

1. Módulos sin dependencias de otros custom → se pueden probar aislados (primero)
2. Módulos que dependen de otros custom → probar después del módulo base
3. Reportes → siempre al final (necesitan datos de los flujos anteriores)

El orden de prueba recomendado usa esta lógica y se incluye al final del informe.
