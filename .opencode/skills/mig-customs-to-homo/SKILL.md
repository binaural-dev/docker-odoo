---
name: mig-customs-to-homo
description: Detecta referencias a modulos integra-addons (binaural_*) en modulos custom y las migra a odoo-venezuela (l10n_ve_*) cuando existe un equivalente. Funciona en cualquier proyecto (higea, pcshop, inversiones2050, etc.) detectando automaticamente la estructura. Usar SOLO cuando el usuario pida homologar/migrar customs a odoo-venezuela o cuando modulos custom fallen por depender de modulos integra-addons ya migrados.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: migration
---

# mig-customs-to-homo

Migra modulos custom del cliente que referencian vistas, templates, records o modelos de modulos `integra-addons/` (prefijo `binaural_*`) hacia sus equivalentes en `odoo-venezuela/` (prefijo `l10n_ve_*`).

## Deteccion automatica de estructura

El agente detecta automaticamente la estructura del proyecto donde se ejecuta.

### Submodulos (detectados via .gitmodules)
- `integra-addons/` — Modulos legacy (fuente de referencias `binaural_*`)
- `odoo-venezuela/` — Nuevos modulos (destino, referencias `l10n_ve_*`)
- `third-party-addons/` — Terceros (NUNCA modificar)

### Customs a migrar (detectados automaticamente)
Todos los directorios en la raiz que contengan `__manifest__.py`, EXCLUYENDO:
- Submodulos (integra-addons, odoo-venezuela, third-party-addons)
- `client_addons/` (si existe)

Comando de deteccion:
```bash
ROOT=$(pwd)
SUBMODULES=$(grep 'path = ' "$ROOT/.gitmodules" 2>/dev/null | sed 's/.*path = //; s/[[:space:]]//g' | tr '\n' '|')
CUSTOMS=""
for d in "$ROOT"/*/; do
    dirname=$(basename "$d")
    [[ "$dirname" =~ ^($SUBMODULES)$ ]] && continue
    [[ "$dirname" == "client_addons" ]] && continue
    [ -f "$d/__manifest__.py" ] && CUSTOMS="$CUSTOMS $dirname"
done
```

## Proceso de migracion (PASO A PASO)

### Paso 1: Identificar modulos custom que referencian integra-addons

Buscar en TODOS los modulos custom detectados (excluyendo submodulos y `third-party-addons/`):

- **En `__manifest__.py`**: dependencias `"binaural_*"` en la lista `depends`
- **En XML**: `t-call="binaural_*.*"`, `t-inherit="binaural_*.*"`, `inherit_id="ref('binaural_*.*')"`, `id="binaural_*.*"`
- **En Python**: `_inherit = "report.binaural_*.*"`, `ref("binaural_*.*")`, cadenas que contengan `"binaural_*."`
- **En JS/XML estatico**: `t-name="binaural_*.*"`, `t-inherit="binaural_*.*"`

### Paso 2: Para cada referencia encontrada, clasificar

Para cada referencia a `binaural_X.some_id`, seguir este flujo de decisión:

```
1. ¿Existe integra-addons/binaural_X/ como módulo FUNCIONAL?
   ├─ Verificar: tiene __manifest__.py? El ID some_id existe dentro del módulo?
   │
   ├─ SÍ (funcional + ID presente) → CASO A: CONSERVAR
   │
   └─ NO (remanente sin manifest, o el ID no existe en el módulo) →
         │
         2. ¿Existe equivalente l10n_ve_* en odoo-venezuela/?
            │
            ├─ SÍ → CASO B: MIGRAR
            │
            └─ NO → CASO C: HUÉRFANA (reportar revisión manual)
```

**Validación de "funcional" en integra-addons:**
```bash
# Verificar que el módulo tiene __manifest__.py
test -f "integra-addons/binaural_X/__manifest__.py" || echo "REMANENTE"

# Verificar que el ID externo específico existe dentro del módulo
grep -r "some_id" "integra-addons/binaural_X/" --include="*.xml" --include="*.csv" --include="*.py" | head -1 || echo "ID_NO_ENCONTRADO"
```

Si el módulo no tiene `__manifest__.py`, es un **remanente** (dead code). Tratarlo como si no existiera en integra-addons y continuar al paso 2.

#### CASO A: No migrar (existe en integra)

El módulo existe **funcionalmente** en integra-addons Y el ID específico está presente. Dejar la referencia como está. Reportar como **"No migrada — existe en integra"**.

#### CASO B: Migrar

El módulo fue migrado a odoo-venezuela. Buscar el ID equivalente usando la tabla de mapeo y reemplazar. Reportar como **"Migrada"**.

#### CASO C: Huérfana

El ID no existe ni en integra-addons (funcional) ni tiene equivalente en odoo-venezuela. Reportar como **"No migrada — huérfana"** para revisión manual.

Si el archivo que contiene la referencia es código muerto (no está referenciado en los assets del `__manifest__.py` del módulo), se puede eliminar directamente.

### Tabla de mapeo binaural_* → l10n_ve_*

| Modulo viejo (borrado) | Modulo nuevo |
|---|---|
| `binaural_invoice` | `l10n_ve_invoice` |
| `binaural_payment_extension` | `l10n_ve_payment_extension` |
| `binaural_stock` | `l10n_ve_stock` |
| `binaural_sale` | `l10n_ve_sale` |
| `binaural_purchase` | `l10n_ve_purchase` |
| `binaural_accountant` | `l10n_ve_accountant` |
| `binaural_rate` | `l10n_ve_rate` |
| `binaural_tax` | `l10n_ve_tax` |
| `binaural_base` | `l10n_ve_base` |
| `binaural_igtf` | `l10n_ve_igtf` |
| `binaural_contact` | `l10n_ve_contact` |
| `binaural_location` | `l10n_ve_location` |
| `binaural_pos` | `l10n_ve_pos` |
| `binaural_filter_partner` | `l10n_ve_filter_partner` |
| `binaural_iot_mf` | `l10n_ve_iot_mf` |
| `binaural_pos_mf` | `l10n_ve_pos_mf` |
| `binaural_stock_accountant` | `l10n_ve_stock_account` |
| `binaural_currency_rate_live` | `l10n_ve_currency_rate_live` |
| `binaural_tax_payer` | `l10n_ve_tax_payer` |

Luego, buscar el external ID equivalente. Estrategias en orden:

1. **Buscar en el modulo nuevo** el mismo nombre de external ID (`grep -r "some_id" "odoo-venezuela/<modulo_nuevo>/"`)
2. **Patron comun de renombre**: `_binaural_*` → `_l10n_ve_*` en nombres de templates/records (ej: `template_invoice_free_form_binaural_invoice` → `template_invoice_free_form_l10n_ve_invoice`)
3. **Patron de paperformat**: Algunos paperformats conservan el sufijo `_binaural_*` (ej: `invoice_free_form_paperformat_binaural_invoice` se convierte en `l10n_ve_invoice.invoice_free_form_paperformat_binaural_invoice`)
4. Si no se encuentra equivalente → **FLAG para revision manual**

**IMPORTANTE**: Antes de reemplazar, VERIFICAR que el external ID equivalente EXISTE en el modulo nuevo (usar `grep` en `odoo-venezuela/<modulo>/`).

#### Modulos sin mapping table

El modulo `binaural_X` existe en integra-addons **funcional** (con `__manifest__.py`) pero no tiene equivalente en odoo-venezuela (son modulos que nunca se migraron, ej: `binaural_brand`, `binaural_hr_payroll`, `binaural_shopify`, etc.).

- Verificar si el ID específico existe en `integra-addons/binaural_X/`:
  - **SI existe** → CASO A (no migrar, existe en integra funcional)
  - **NO existe** → CASO C (huérfana — el ID especifico no existe en ninguna parte)

#### Modulos en mapping table sin ID equivalente confirmado

Si el modulo origen esta en la tabla de mapeo pero el ID especifico no se encuentra ni en integra-addons (funcional) ni en odoo-venezuela → **CASO C (huérfana)**.

### Paso 3: Tipos de cambios a aplicar

#### En `__manifest__.py`

Cambiar dependencias en la lista `depends`:
```python
# Antes
"binaural_invoice",
# Despues
"l10n_ve_invoice",
```

#### En XML (QWeb templates)

```xml
<!-- Antes -->
<t t-call="binaural_invoice.template_invoice_free_form_binaural_invoice" t-lang="lang"/>
<!-- Despues -->
<t t-call="l10n_ve_invoice.template_invoice_free_form_l10n_ve_invoice" t-lang="lang"/>
```

#### En XML (records/views)

```xml
<!-- Antes: record id perteneciente a otro modulo -->
<record id="binaural_invoice.invoice_free_form_paperformat_binaural_invoice" model="...">
<!-- Despues -->
<record id="l10n_ve_invoice.invoice_free_form_paperformat_binaural_invoice" model="...">

<!-- Antes: inherit_id -->
<field name="inherit_id" ref="binaural_invoice.report_freeform_document"/>
<!-- Despues -->
<field name="inherit_id" ref="l10n_ve_invoice.report_freeform_document"/>

<!-- Antes: ref= en atributos -->
<field name="inherit_id" ref="binaural_sale.view_sale_order_form_binaural_sales"/>
<!-- Despues -->
<field name="inherit_id" ref="l10n_ve_sale.view_sale_order_form_l10n_ve_sales"/>
```

#### En Python (model inheritance)

```python
# Antes
_inherit = "report.binaural_payment_extension.retention_voucher_template"
# Despues
_inherit = "report.l10n_ve_payment_extension.retention_voucher_template"
```

#### En JS/XML estatico (OWL templates)

Si el modulo origen no existe y el destino tiene un template equivalente, migrar. Si el modulo origen existe en integra-addons y el ID tambien, NO migrar.

```xml
<!-- Antes -->
<t t-inherit="binaural_pos_receipt.ReceiptScreen" ...
<!-- binaural_pos_receipt SI existe en integra-addons -> verificar si el ID especifico existe -->
```

### Paso 4: Codigo muerto (dead code)

Si un archivo referenciado NO está declarado en los `assets` del `__manifest__.py` del módulo que lo contiene, es probablemente **código muerto** (reliquia de migraciones anteriores). En ese caso:
- Se puede **eliminar** directamente sin migrar
- Reportarlo como **"❌ No migrada — huérfana (archivo eliminado por código muerto)"**

### Paso 5: Casos especiales conocidos

1. **`binaural_pos_receipt`**: Este modulo SI existe en integra-addons y NO tiene equivalente completo en odoo-venezuela. `l10n_ve_pos` tiene su propio `ReceiptScreen` con `owl="1"` que es diferente. **No migrar referencias a `binaural_pos_receipt` si el external ID existe en integra-addons. Si el ID especifico no existe, reportar FLAG manual.**

2. **`binaural_purchase` / `binaural_base` / `binaural_stock_accountant`**: Existen en `integra-addons/` pero algunas son **remanentes** (sin `__manifest__.py`). Verificar funcionalidad: si tiene `__manifest__.py` Y el ID externo existe → CASO A (conservar). Si es remanente o el ID no existe → tratar como si no estuviera en integra y continuar a CASO B/C.

3. **`binaural_subsidiary` y submodulos relacionados**: Existen en `integra-addons/` pero ya dependen de `l10n_ve_*`. No tienen equivalentes en odoo-venezuela. Verificar ID por ID dentro de integra-addons.

4. **`third-party-addons/`**: NUNCA modificar esta carpeta. Solo reportar si se encuentran referencias.

5. **Modulos sin mapping table** (~100+ modulos como `binaural_brand`, `binaural_hr_payroll`, `binaural_shopify`, etc.): Existen SOLO en integra-addons. Verificar funcionalidad: si tiene `__manifest__.py` Y el ID externo existe → CASO A (conservar). Si es remanente o el ID no existe → CASO C (huérfana).

## Verificacion final

Despues de hacer cambios, ejecutar el comando dinamico con los customs detectados:

```bash
ROOT=$(pwd)
SUBMODULES=$(grep 'path = ' "$ROOT/.gitmodules" 2>/dev/null | sed 's/.*path = //; s/[[:space:]]//g' | tr '\n' '|')
CUSTOMS=""
for d in "$ROOT"/*/; do
    dirname=$(basename "$d")
    [[ "$dirname" =~ ^($SUBMODULES)$ ]] && continue
    [[ "$dirname" == "client_addons" ]] && continue
    [ -f "$d/__manifest__.py" ] && CUSTOMS="$CUSTOMS $dirname"
done

grep -r "binaural_" $(for c in $CUSTOMS; do echo "$c/"; done) --include="*.py" --include="*.xml" --include="*.js" | grep -v "^Binary"
```

Esto mostrara cualquier referencia residual a `binaural_*` que no se haya migrado.

## Reporte final

Al terminar, entregar un resumen con:

### 1. Proyecto detectado y customs identificados
### 2. Archivos modificados y cambios realizados
### 3. Clasificación de referencias (3 categorías)

| Categoría | Significado | Acción |
|---|---|---|
| ✅ **Migradas** | Referencia migrada de binaural_* → l10n_ve_* | Reemplazo aplicado |
| ⚠️ **No migradas — existe en integra** | El módulo es funcional en integra-addons y el ID externo existe | Referencia conservada (no requiere cambio) |
| ❌ **No migradas — huérfanas** | No existe ni en integra-addons (funcional) ni en odoo-venezuela | Reportar para revisión manual o eliminar si es código muerto |

Cada referencia debe incluir: archivo, línea, módulo/ID referenciado, y el resultado de la validación funcional en integra-addons.

### 4. Referencias en `third-party-addons/` (si las hay)
