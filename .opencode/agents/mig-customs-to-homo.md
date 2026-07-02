---
description: Detecta referencias a modulos integra-addons (binaural_*) en modulos custom y las migra a odoo-venezuela (l10n_ve_*) cuando existe un equivalente. Funciona en cualquier proyecto (higea, pcshop, inversiones2050, etc.) detectando automaticamente la estructura. Usar SOLO cuando el usuario pida homologar/migrar customs a odoo-venezuela o cuando modulos custom fallen por depender de modulos integra-addons ya migrados.
mode: subagent
model: inherit
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

Para cada referencia a `binaural_X.some_id`:

1. **¿Existe el directorio `integra-addons/binaural_X/`?**
   - **NO** → El modulo fue migrado. Saltar a "CASO A" (buscar equivalente en odoo-venezuela)
   - **SI** → Continuar al paso 2

2. **¿Existe `some_id` DENTRO de `integra-addons/binaural_X/`?**
   - **SI** → CASO B: NO MIGRAR (la referencia es valida)
   - **NO** → El record/template especifico fue movido. Saltar a "CASO A" (buscar equivalente en odoo-venezuela)

#### CASO A: Buscar equivalente en odoo-venezuela

Usar la tabla de mapeo para encontrar el modulo destino:

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

#### CASO B: NO migrar

El modulo existe en integra-addons Y el ID referenciado esta presente. Dejar la referencia como esta.

#### CASO C: Modulo en mapping table sin equivalente confirmado

Si el modulo origen esta en la tabla de mapeo pero el ID especifico no se encuentra ni en integra-addons ni en odoo-venezuela → **FLAG para revision manual**.

#### CASO D: Modulo referenciado NO esta en la tabla de mapeo

El modulo `binaural_X` existe en integra-addons pero no tiene equivalente en odoo-venezuela (son modulos que nunca se migraron, ej: `binaural_brand`, `binaural_hr_payroll`, `binaural_shopify`, etc.).

- Verificar si el ID específico existe en `integra-addons/binaural_X/`
  - **SI existe** → NO MIGRAR
  - **NO existe** → FLAG para revision manual (podria ser un ID que se movio a otro modulo o se elimino)

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
<!-- Despues: verificar si el nombre cambio o solo el modulo -->
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

### Paso 4: Casos especiales conocidos

1. **`binaural_pos_receipt`**: Este modulo SI existe en integra-addons y NO tiene equivalente completo en odoo-venezuela. `l10n_ve_pos` tiene su propio `ReceiptScreen` con `owl="1"` que es diferente. **No migrar referencias a `binaural_pos_receipt` si el external ID existe en integra-addons. Si el ID especifico no existe, reportar FLAG manual.**

2. **`binaural_purchase` / `binaural_base` / `binaural_stock_accountant`**: Estos modulos aun existen en `integra-addons/` PERO tambien tienen equivalentes en `odoo-venezuela/`. Algunas referencias dentro de ellos YA apuntan a modulos `l10n_ve_*`. Verificar ID por ID: si existe en integra no migrar; si no existe, buscar en odoo-venezuela.

3. **`binaural_subsidiary` y submodulos relacionados**: Existen en `integra-addons/` pero ya dependen de `l10n_ve_*`. No tienen equivalentes en odoo-venezuela. Verificar ID por ID dentro de integra-addons.

4. **`third-party-addons/`**: NUNCA modificar esta carpeta. Solo reportar si se encuentran referencias.

5. **Modulos sin mapping table** (~100+ modulos como `binaural_brand`, `binaural_hr_payroll`, `binaural_shopify`, etc.): Existen SOLO en integra-addons. No migrar. Verificar que el ID exista en integra; si no existe, FLAG manual.

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
- Proyecto detectado y customs identificados
- Lista de archivos modificados y cambios realizados
- Lista de referencias migradas (CASO A)
- Lista de referencias que se mantuvieron porque el ID existe en integra-addons (CASO B)
- Lista de referencias que NO se pudieron migrar por falta de equivalente (FLAGS manuales)
- Lista de referencias en `third-party-addons/` (si las hay)
