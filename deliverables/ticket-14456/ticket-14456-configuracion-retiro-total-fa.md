# Ticket 14456 — Creación de Check para retiro total F.A.

**Análisis técnico-funcional y plan de configuración**

| | |
|---|---|
| Ticket | 14456 — "Creacion de Check para retiro total F.A" |
| Origen | Helpdesk Binaural (binaural.odoo.com), compañía Binaural C.A |
| Cliente / base analizada | INDUVAR — base `17_idv_stg` (instancia local `idv`, puerto 8073) |
| Módulos involucrados | `binaural_hr_savings_fund` 17.0.1.4.0, `induvar_hr_savings_fund` 17.0.1.0.1 |
| Dirigido a | Consultor funcional (ejecuta la configuración) y líder técnico (aprueba el cierre) |
| Conclusión | No requiere desarrollo. Es configuración. |

---

## 1. Resumen ejecutivo

El ticket solicita "la creación de un check en las otras entradas para detectar si es retiro total de fondo de ahorro" cuya función sea llevar el monto del retiro total a las otras entradas de la nómina, alimentar las líneas de movimientos del fondo y debitar el capital.

**Ese mecanismo ya existe completo en `binaural_hr_savings_fund` y está probado.** El módulo instala el tipo de otra entrada `PAGO_FA` con el check `is_savings_fund_advance_payment`, y su lógica ya contempla el retiro total: al confirmar el movimiento se crea la línea negativa en el fondo y el capital baja solo; al calcular el recibo, el módulo inyecta la otra entrada con el monto pendiente; al confirmar el recibo, el movimiento pasa a "Pagado".

Lo que falta es **cablearlo en la estructura salarial donde se paga el retiro total**. En `17_idv_stg` solo la estructura 141 "Incentivo al Ahorro" tiene una regla con ese check, y ahí el circuito funciona (219 líneas de recibo generadas, 3 movimientos ya conciliados). La estructura 47 "Liquidación" —el lugar natural del retiro total— no tiene ninguna regla con el check; en su lugar hay una regla manual que paga el monto pero no toca el fondo. Esa es exactamente la carencia que describe el ticket.

Además hay tres registros de configuración espurios que hay que retirar (un tipo de entrada `PAGO_FA` duplicado sin el check, un `RET_AHORRO` muerto y una regla manual `INCENT_AHORRO`), y una corrección de categoría sin la cual la línea aparecería en el recibo sin afectar el neto.

**Implementar el check tal como lo pide el ticket sería un retroceso**: crearía una segunda vía de entrada manejada desde el recibo, que se salta las validaciones del movimiento y duplicaría el débito de capital. Ver sección 8.

---

## 2. Estado del ambiente — bloqueante previo

Antes de aplicar cualquier configuración hay que resolver un problema de despliegue detectado durante este análisis:

La instancia `idv` carga sus addons desde `src/custom/idv/integra-addons` (variable `INSTANCE_ADDONS` del contenedor `odoo-idv`), **no** desde `src/integra-addons`. En esa ruta el directorio `binaural_hr_savings_fund` quedó vacío —solo sobreviven `models/`, `wizard/` y `__pycache__`, sin `__manifest__.py` ni `__init__.py`— tras un cambio de rama. Lo mismo ocurre con `induvar_hr_savings_fund`.

Consecuencia observable hoy en la base `17_idv_stg`:

| Síntoma | Detalle |
|---|---|
| Modelos inexistentes en runtime | `hr.savings.fund` y `hr.savings.fund.movement` responden "El objeto ... no existe" |
| Campos ausentes del registro | `is_savings_fund_advance_payment` no aparece en `fields_get` de `hr.salary.rule` ni de `hr.payslip.input.type`; el log muestra `ValueError: Invalid field 'is_savings_fund_advance_payment' on model 'hr.payslip.input.type'` |
| Versión reportada | `ir.module.module.installed_version` cae al valor por defecto `17.0.1.0` (señal inequívoca de que el manifiesto no se encuentra en disco), mientras `latest_version` conserva `17.0.1.4.0` |

Los **datos siguen intactos en PostgreSQL** (columnas, fondos, líneas y movimientos): es solo el código el que falta en la ruta que la instancia lee. Todo el diagnóstico de este documento se hizo con consultas SQL de solo lectura sobre `17_idv_stg`.

> **Acción previa obligatoria:** restaurar `binaural_hr_savings_fund` e `induvar_hr_savings_fund` en `src/custom/idv/integra-addons` / `src/custom/idv`, reiniciar la instancia y actualizar ambos módulos. Sin esto los checkboxes y menús del fondo de ahorro no se ven en la interfaz —lo cual, dicho sea de paso, refuerza la hipótesis de por qué se abrió el ticket.

---

## 3. Cómo funciona el retiro total en el módulo

El circuito completo, con los nombres reales. Rutas relativas a `src/integra-addons/binaural_hr_savings_fund/`.

### 3.1 Los tres artefactos que sostienen el mecanismo

| Artefacto | Dónde se define | Qué es |
|---|---|---|
| Tipo de otra entrada `PAGO_FA` | `data/hr_payslip_input_type_data.xml`, XML ID `binaural_hr_savings_fund.input_type_savings_fund_advance_payment` | Registro con `is_savings_fund_advance_payment = True`. **Este es el check que pide el ticket.** Se instala con el módulo; no hay que crearlo. |
| Check en el tipo de entrada | `models/hr_payslip_input_type.py` → campo `is_savings_fund_advance_payment` | Etiqueta: "Pago de Anticipo - Fondo de Ahorro" (en INDUVAR: "Pago de Anticipo - Incentivo al Ahorro") |
| Check en la regla salarial | `models/hr_salary_rule.py:18` → campo `is_savings_fund_advance_payment` | Etiqueta: "Pago Anticipos - Fondo de Ahorro" (en INDUVAR: "Pago Anticipos - Incentivo al Ahorro"). **Es el interruptor que activa todo el circuito en una estructura.** |

### 3.2 El flujo, paso a paso

| # | Disparador | Código | Efecto |
|---|---|---|---|
| 1 | El analista crea el movimiento con tipo "Retiro Total" | `hr_savings_fund_movement.py`, `_onchange_total_withdrawal` (líneas 171-175) | El campo `amount` se autocompleta con `fund_id.capital` y `foreign_amount` con `foreign_capital` |
| 2 | Marca **"Pagar por Nómina"** (`pay_by_payroll`) y pulsa Confirmar | `action_confirm` (línea 197) | Valida fondo activo, estado borrador, monto > 0, y que el monto no exceda el capital disponible |
| 3 | (dentro de Confirmar) | `action_confirm`, líneas 210-212 | **Refija** `amount = fund_id.capital` en el instante de la confirmación, para que un borrador viejo no arrastre un capital desactualizado |
| 4 | (dentro de Confirmar) | `action_confirm`, líneas 241-253 | Crea una `hr.savings.fund.line` con `amount = -move.amount` y `movement_type = 'total_withdrawal'`. **Esto es "alimentar las líneas de movimientos" del ticket.** |
| 5 | Automático | `hr_savings_fund.py::_compute_amounts` (línea 114) | `capital = sum(line_ids.amount)` → el capital **se debita solo**. **Esto es "debitar el retiro total del capital" del ticket.** |
| 6 | Automático | `_compute_payment_state` (líneas 117-129) | `payment_state = 'pending'` |
| 7 | El analista calcula el recibo | `hr_payslip.py::compute_sheet` (línea 23) llama a `_update_savings_fund_advance_inputs` (línea 135) **antes** del `super()` | Borra la otra entrada anterior de tipo `PAGO_FA` e inyecta una nueva con el total pendiente |
| 8 | (dentro del paso 7) | `_get_savings_fund_movements_to_pay` (línea 112) | Busca movimientos con `state='confirmed'`, `pay_by_payroll=True`, `payment_payslip_id=False`, `date <= date_to` y `movement_type != 'loan_amortization'`. **El retiro total entra por aquí: el filtro excluye solo las amortizaciones de préstamo.** |
| 9 | (dentro del paso 7) | `_update_savings_fund_advance_inputs`, líneas 150-152 | **`if not any(rule.is_savings_fund_advance_payment for rule in slip.struct_id.rule_ids): continue`** — si la estructura no tiene una regla con el check, **no inyecta nada**. Esta línea es la clave de todo el ticket. |
| 10 | Cálculo del recibo | La regla marcada, con `result = inputs['PAGO_FA'].amount if 'PAGO_FA' in inputs else 0` | Genera la línea de recibo con el monto del retiro |
| 11 | El analista confirma el recibo | `action_payslip_done` (línea 8) → `_register_savings_fund_advance_payments` (línea 167) | Consume los movimientos en orden de fecha hasta agotar el total efectivamente pagado y les asigna `payment_payslip_id` → `payment_state = 'paid'` |
| 12 | Si se cancela el recibo | `action_payslip_cancel` (línea 16) | Limpia `payment_payslip_id` de los movimientos → vuelven a "Pendiente" |

### 3.3 Diagrama

```
  Fondos de Ahorro
        │
        ▼
  [Movimiento: Retiro Total]  ── amount = capital (autocompletado, solo lectura)
        │                         pay_by_payroll = True
        │  Confirmar
        ▼
  action_confirm ──┬──► hr.savings.fund.line  (amount = -capital,
                   │                           movement_type = total_withdrawal)
                   │            │
                   │            ▼
                   │      _compute_amounts  ──► capital del fondo = 0
                   │
                   └──► payment_state = "Pendiente"
                                │
                                ▼
  [Recibo de Liquidación] ── compute_sheet()
                                │
                                ▼
              _update_savings_fund_advance_inputs()
                                │
              ¿la estructura tiene una regla con el check
               "Pago Anticipos - Fondo de Ahorro"?
                       │                    │
                      NO                   SÍ
                       │                    │
                 no hace nada        inyecta otra entrada PAGO_FA
                (situación actual     con el total pendiente
                 de la estructura 47)         │
                                              ▼
                                    la regla marcada calcula
                                    result = inputs['PAGO_FA'].amount
                                              │
                                              ▼
                                  Confirmar recibo → action_payslip_done()
                                              │
                                              ▼
                        _register_savings_fund_advance_payments()
                                              │
                                              ▼
                                   movimiento = "Pagado"
```

### 3.4 Evidencia de que ya está soportado y probado

- `README.md` del módulo, líneas 84-90: *"El tipo de otra entrada `PAGO_FA` lo instala este módulo (no hay que crearlo). Los movimientos (Anticipo FA / Anticipo de Intereses / Retiro Total) confirmados con «Pagar por Nómina» activo quedan «Pendiente» y el próximo recibo calculado los paga una sola vez (todos los pendientes en una sola otra entrada); al confirmar el recibo pasan a «Pagado». Cancelar el recibo los devuelve a «Pendiente»."*
- Pruebas unitarias existentes:
  - `tests/test_savings_fund_movement.py::test_a_total_withdrawal_empties_the_fund` (línea 197)
  - `tests/test_savings_fund_movement.py::test_the_total_withdrawal_line_negates_the_current_capital` (línea 207)
  - `tests/test_savings_fund_movement.py::test_a_stale_total_withdrawal_is_clamped_to_the_capital` (línea 186)
  - `tests/test_savings_fund_payslip.py::test_a_pending_movement_creates_the_advance_input` (línea 160)
  - `tests/test_savings_fund_payslip.py::test_a_structure_without_the_advance_rule_creates_no_input` (línea 206) — la prueba que documenta precisamente la causa del ticket
  - `tests/test_savings_fund_payslip.py::test_cancelling_the_payslip_returns_the_movement_to_pending` (línea 328)

El código en `src/integra-addons/binaural_hr_savings_fund` es **idéntico** a `origin/l10nve_17.0` (diff vacío).

### 3.5 Particularidad de INDUVAR

El módulo `induvar_hr_savings_fund` 17.0.1.0.1 adapta el fondo para este cliente:

- Renombra las etiquetas: "Fondo de Ahorro" → **"Incentivo al Ahorro"**; el tipo de movimiento `advance` se muestra como **"Retiro Parcial IA"** y `total_withdrawal` como **"Retiro Total IA"**.
- Bloquea por `@api.constrains` y `@api.onchange` los tipos `interest_advance` y `loan_amortization` ("This option is disabled for the Savings Incentive"). En INDUVAR solo quedan operativos **Retiro Parcial** y **Retiro Total**.
- Anula la generación automática de intereses (`get_savings_fund_interest` devuelve `None`).

Esto simplifica el escenario: la otra entrada `PAGO_FA` en INDUVAR solo puede contener retiros parciales y retiros totales.

---

## 4. Diagnóstico de la base `17_idv_stg`

Datos obtenidos por consulta SQL de solo lectura sobre la base al 05/08/2026.

### 4.1 Estructuras salariales frente a las reglas del fondo

Solo se listan las estructuras relevantes. "Reglas" cuenta reglas **activas** (entre paréntesis, las archivadas).

| ID | Estructura | Cía. | Reglas | Check "Pago Anticipos" | Aporte Empleado | Aporte Empresa | Recibos |
|---:|---|---|---:|:---:|:---:|:---:|---:|
| 37 | Nómina Empleados | INDUVAR | 96 (124) | **NO** | Sí (`EMP_FA`) | Sí (`PAT_FA`) | 2.791 |
| 38 | Nómina Ejecutiva | INDUVAR | 89 (192) | NO | No | No | 264 |
| 39 | Nómina Obreros | INDUVAR | 71 (155) | NO | No | No | 6.453 |
| 40 | Ayuda Semanal | INDUVAR | 33 (38) | NO | No | No | 12.197 |
| 44 | Vacaciones Empleados | INDUVAR | 28 (76) | NO | No | No | 216 |
| **47** | **Liquidación** | INDUVAR | 67 (17) | **NO** | No | No | **0** |
| 52 | Vacaciones Obreros | INDUVAR | 28 (76) | NO | No | No | 264 |
| 63 | Vacaciones Ejecutiva | INDUVAR | 28 (79) | NO | No | No | 25 |
| **141** | **Incentivo al Ahorro** | INDUVAR | 3 (2) | **SÍ** (`PAGO_FA`, id 10814) | No | No | **219** |

Las 66 estructuras restantes de la base (SAVONE, TEC ENVASE, JABONERÍA CARACAS, BERSA-CHEM y el resto de INDUVAR) no tienen ninguna regla del fondo de ahorro.

**Solo una regla en toda la base lleva el check activo**: id 10814 `PAGO_FA` "Pago Anticipo FA", estructura 141, secuencia 41, categoría **Asignación (ASIG)**, condición Ninguna, cómputo Código Python:

```python
result = inputs['PAGO_FA'].amount if 'PAGO_FA' in inputs else 0
```

La estructura 141 es un esquema dedicado de 3 reglas activas —`DISPO_INCEN` (Base, disponible del incentivo), `PAGO_FA` (Asignación, el pago) y `TA_AHORRO` (Gross, neto a pagar que suma `categories.get("ASIG")`)— con 219 recibos. Es decir: **hoy INDUVAR corre un recibo aparte solo para pagar el incentivo, y ahí el mecanismo del módulo funciona correctamente.**

Evidencia de funcionamiento en la estructura 141: 219 líneas de recibo generadas por la regla 10814 por un total de Bs. 319.998,81, y 7 otras entradas `PAGO_FA` inyectadas automáticamente por el módulo.

### 4.2 La regla manual de la estructura 47 "Liquidación"

| Campo | Valor |
|---|---|
| ID / Código | 1848 / `INCENT_AHORRO` |
| Nombre | Incentivo Ahorro Liquidación |
| Secuencia | 45 |
| Categoría | **Otros cálculos (OC)** |
| Check "Pago Anticipos - Fondo de Ahorro" | **Apagado** |
| Condición | Python |
| Cómputo | `incentivo = inputs['INCENT_AHORRO'].amount` / `foreign_result = incentivo` / `result = foreign_result / foreign_inverse_rate` |
| Tipo de otra entrada que lee | id 94 `INCENT_AHORRO` "Incentivo Ahorro Liquidación", publicado solo en la estructura 47, **0 líneas usadas** |

Esta regla paga un monto que el analista teclea a mano en dólares, y **no crea la línea del fondo, no debita el capital y no concilia ningún movimiento**. Es exactamente la carencia que describe el ticket.

### 4.3 Tipos de otra entrada relacionados con el fondo

| ID | Código | Nombre visible | Check FA | Otros checks | Estructuras publicadas | Líneas usadas | Veredicto |
|---:|---|---|:---:|---|---|---:|---|
| 215 | `PAGO_FA` | Savings Fund Advance Payment | **SÍ** | — | (vacío = todas) | **7** | **El bueno.** Lo instala el módulo (XML ID `binaural_hr_savings_fund.input_type_savings_fund_advance_payment`) |
| 221 | `PAGO_FA` | Pago Anticipo FA | **NO** | "Es entrada de Anticipo" activo | 37, 38, 39, 40, 44, 52, 63 | 0 | **Duplicado a eliminar.** Colisión de código |
| 220 | `RET_AHORRO` | Retiro Incentivo al Ahorro | NO | — | 37, 38, 39, 40, 44, 52, 63 | 0 | **Configuración muerta.** Ninguna regla activa lo lee |
| 94 | `INCENT_AHORRO` | Incentivo Ahorro Liquidación | NO | — | 47 | 0 | Alimenta la regla manual 1848 |

Sobre el registro **id 221**: es el que aparece en el pantallazo del ticket. Tiene el check "Es entrada de Anticipo" (`is_advance_input`) activado y el de fondo de ahorro apagado, y es el único `PAGO_FA` publicado en las estructuras de nómina real (37, 38, 39, 40...). El registro correcto —id 215— se muestra en inglés ("Savings Fund Advance Payment", el campo `name` de `hr.payslip.input.type` no es traducible) y tiene `struct_ids` vacío. **Quien abrió el ticket miró el registro 221, no vio ningún check de retiro total y concluyó que no existía.** El check sí existe: está en el registro 215.

### 4.4 Riesgo real del código `PAGO_FA` duplicado

En Odoo 17, `hr_payslip.py::_get_localdict` construye el diccionario `inputs` **indexado por código**, y cuando dos líneas comparten código las envuelve en un agregador cuyo `amount` **suma** ambas (`ProxyHrPayslipInput.amount`, `src/enterprise-17/hr_payroll/models/hr_payslip.py:1438-1442`).

Además, `_update_savings_fund_advance_inputs` borra las líneas obsoletas filtrando por `input_type_id.is_savings_fund_advance_payment` — es decir, **no toca** una línea manual del tipo 221, porque ese tipo tiene el check apagado.

Consecuencia: si en un mismo recibo conviven la línea automática del tipo 215 y una línea manual del tipo 221, `inputs['PAGO_FA'].amount` devuelve la **suma** de ambas y el trabajador cobra dos veces. No es una sobrescritura silenciosa: es un pago doble silencioso.

### 4.5 Movimientos y fondos

**Nunca se ha ejecutado un retiro total en esta base.** Los 7 movimientos existentes son todos de tipo `advance` (Retiro Parcial IA):

| Tipo | Estado | Pagar por Nómina | Conciliado | Cantidad | Monto |
|---|---|:---:|:---:|---:|---:|
| advance | Confirmado | No | No | 1 | 25.997,23 |
| advance | Confirmado | Sí | No | 2 | 10.001,04 |
| advance | Confirmado | Sí | **Sí** | 3 | 299.996,73 |
| advance | Borrador | Sí | No | 1 | 3.999,05 |
| **total_withdrawal** | — | — | — | **0** | **0,00** |

Los 3 movimientos conciliados apuntan a los recibos SLIP/103822, SLIP/103823 y SLIP/103824 de la estructura 141 (hoy en borrador tras un reseteo posterior; `payment_payslip_id` solo se limpia al **cancelar** el recibo, no al devolverlo a borrador).

Líneas del fondo (`hr.savings.fund.line`), 166 en total:

| Tipo de línea | Cantidad | Total (Bs.) |
|---|---:|---:|
| Saldo inicial | 71 | 4.887.855,23 |
| Aporte empresa | 42 | 1.789.529,46 |
| Aporte empleado | 44 | 1.533.675,61 |
| Anticipo (retiro parcial) | 9 | −401.001,79 |
| **Retiro total** | **0** | **0,00** |

Fondos y porcentajes:

| Compañía | Fondos activos | Con porcentaje | Capital acumulado | Porcentajes definidos |
|---|---:|---:|---:|---:|
| INDUVAR, S.A | 71 | 71 | 7.810.058,51 | 2 (5 % y 10 %) |
| SAVONE COSMETICOS, C.A | 0 | 0 | — | 0 |
| TEC ENVASE, C.A | 0 | 0 | — | 0 |
| JABONERIA CARACAS, C.A | 0 | 0 | — | 0 |
| BERSA-CHEM ANDINA S.A | 0 | 0 | — | 0 |

---

## 5. Configuración requerida, paso a paso

### Paso 1 (crítico) — Crear la regla del pago en la estructura 47 "Liquidación"

Ruta: **Nómina → Configuración → Estructuras Salariales → Liquidación (id 47) → pestaña Reglas Salariales → Agregar línea**.

| Campo | Valor a capturar |
|---|---|
| Nombre | `Pago Retiro Incentivo al Ahorro` |
| Código | `PAGO_FA` |
| Categoría | **Subsidio (`ALW`)** — ver la nota crítica más abajo |
| Secuencia | `46` (inmediatamente después de la actual `INCENT_AHORRO`, secuencia 45) |
| Condición basada en | **Siempre verdadero** |
| Tipo de importe | **Código Python** |
| Código Python | `result = inputs['PAGO_FA'].amount if 'PAGO_FA' in inputs else 0` |
| Aparece en el recibo | Sí |
| **Pago Anticipos - Incentivo al Ahorro** | **MARCADO** |

El código Python va en **una sola línea, sin sangría inicial**. Cualquier espacio al principio provoca `IndentationError` al calcular el recibo.

> **Nota crítica sobre la categoría.** La regla `NET` de la estructura 47 (id 1828) calcula:
>
> ```python
> asig = (categories.get("ALW") or 0) + (categories.get("OCV") or 0) + (categories.get("BASIC") or 0) + (categories.get("UTILIDADES") or 0)
> ded  = categories.get("DED") + categories.get("RETENCION") + categories.get("DED2") + categories.get("DED3")
> result = asig + ded
> ```
>
> **La categoría "Asignación" (`ASIG`) NO está en esa fórmula.** Si se copia la configuración de la estructura 141 —que sí usa `ASIG`, porque su regla `TA_AHORRO` la suma explícitamente— la línea aparecería en el recibo de liquidación **sin modificar el neto**. Las categorías válidas en la estructura 47 son `BASIC`, `ALW`, `OCV` y `UTILIDADES`; **`ALW` (Subsidio)** es la adecuada y ya tiene 3 reglas activas en esa estructura.
>
> Por el mismo motivo, la regla manual actual `INCENT_AHORRO` (categoría `OC`, "Otros cálculos", tampoco incluida en el `NET`) probablemente nunca ha llegado al neto. Como la estructura 47 tiene **0 recibos**, nadie lo ha detectado.

> **Restricción del módulo.** `hr_salary_rule.py::_check_savings_fund_contribution_per_structure` (líneas 25-77) impide que exista **más de una** regla con el check "Pago Anticipos" por estructura. Si al guardar aparece *"There can only be one Advance Payments - Savings Fund rule per structure"*, es que ya hay otra regla marcada en esa estructura: hay que localizarla y desmarcarla, no crear una segunda.

Repetir este paso en cualquier otra estructura donde se decida pagar retiros (ver Paso 5).

### Paso 2 — Retirar la regla manual `INCENT_AHORRO` de la estructura 47

1. Archivar (o eliminar) la regla salarial id **1848** `INCENT_AHORRO` "Incentivo Ahorro Liquidación" de la estructura 47.
2. Archivar el tipo de otra entrada id **94** `INCENT_AHORRO`, o al menos quitar la estructura 47 de su campo "Disponibilidad en Estructura".

> **Por qué es obligatorio.** Si la regla nueva del Paso 1 y la regla manual conviven, el retiro total se paga dos veces: una por la otra entrada `PAGO_FA` que inyecta el módulo automáticamente, y otra por la otra entrada `INCENT_AHORRO` que el analista sigue capturando a mano por costumbre. Ninguna de las dos vías se entera de la otra.

El tipo 94 tiene **0 líneas usadas**, así que retirarlo no rompe ningún recibo histórico. La regla 1848 tampoco ha producido líneas: la estructura 47 no tiene recibos.

### Paso 3 — Eliminar el tipo de otra entrada duplicado id 221

Ruta: **Nómina → Configuración → Tipos de Otras Entradas**.

Localizar el registro **id 221**, código `PAGO_FA`, nombre "Pago Anticipo FA", con el check "Es entrada de Anticipo" activo, y **eliminarlo** (o archivarlo si se prefiere conservar la traza).

- No tiene XML ID, así que `_unlink_except_master_data` de `hr_payroll` no bloquea el borrado.
- Tiene **0 líneas usadas**: no rompe históricos.
- No confundirlo con el id 215 "Savings Fund Advance Payment", que sí tiene el check del fondo, sí está en uso (7 líneas) y **no debe tocarse**. El 215 tiene además XML ID, por lo que Odoo impediría su borrado con el mensaje *"You cannot delete ... as it is used in another module but you can archive it instead"*.

Riesgo que se elimina: la colisión de código descrita en 4.4 — dos tipos distintos con el mismo código `PAGO_FA` cuyas líneas se **suman** en el diccionario `inputs` del recibo, produciendo un pago doble.

### Paso 4 — Eliminar el tipo de otra entrada id 220 `RET_AHORRO`

Registro **id 220** "Retiro Incentivo al Ahorro", publicado en las estructuras 37, 38, 39, 40, 44, 52 y 63, con **0 líneas usadas** y sin ninguna regla salarial activa que lo lea. Es un intento abandonado de armar el retiro total a mano.

Dejarlo publicado en 7 estructuras invita a que alguien lo capture creyendo que sirve. **Eliminar o archivar.**

(La única regla que menciona `RET_AHORRO` es la id 10817 de la estructura 141, que está **inactiva** y además lee `inputs['PAGO_FA']`, no `RET_AHORRO`. Archivarla también, por higiene.)

### Paso 5 — Decidir el alcance: recibo dedicado o nómina regular

Hay que tomar una decisión funcional explícita, porque determina en cuántas estructuras se repite el Paso 1.

| | **Opción A — mantener el recibo dedicado (estructura 141)** | **Opción B — habilitar también en la nómina regular (37, 38, 39, 40)** |
|---|---|---|
| Configuración | Paso 1 solo en la estructura 47. La 141 sigue como está | Paso 1 en la 47 y además en cada estructura de nómina donde se quiera pagar |
| Cómo se opera | Se corre un recibo aparte de la estructura 141 exclusivamente para pagar retiros parciales | El retiro sale en el mismo recibo de la quincena/mes del trabajador |
| Ventajas | Aislado y trazable; ya está funcionando; no altera el neto de las nóminas regulares ni sus reportes | Menos recibos que procesar; el trabajador cobra todo junto |
| Riesgos | Más recibos que crear y confirmar | El monto entra en las bases de cálculo de las reglas de esa estructura (retenciones, FAOV, etc.) salvo que se excluya expresamente la categoría elegida. **Hay que revisar regla por regla qué categorías consume cada base antes de habilitarlo.** |
| Riesgo compartido | Un movimiento pendiente se inyecta en **todos** los recibos que se calculen para ese trabajador mientras siga pendiente | Igual, y con la Opción B es más probable que coincidan varios (ver nota) |

> **Nota operativa (verificada en la base).** Los movimientos pendientes se marcan como pagados solo al **confirmar** un recibo. Mientras tanto, cada recibo que se calcule para ese trabajador recibe su propia otra entrada `PAGO_FA`. Hoy en `17_idv_stg` los empleados CLARO PAREDES ENMANUEL y FAJARDO CARLOS ALBERTO tienen cada uno **dos** recibos en estado "Verificar" con la misma otra entrada de Bs. 5.000,52, procedente del mismo movimiento pendiente. Al confirmar el primero, el movimiento pasa a "Pagado"; el segundo **conserva** la otra entrada obsoleta y pagaría de nuevo si se confirma sin recalcular.
>
> Regla operativa: **recalcular siempre el recibo justo antes de confirmarlo**, y no dejar varios recibos abiertos para el mismo trabajador con movimientos de fondo pendientes.

**Recomendación:** Opción A para el cierre del ticket 14456 (el retiro total pertenece naturalmente a la liquidación). Opción B, si se quiere, como iniciativa separada previo análisis de las bases de cálculo.

### Paso 6 (fuera del alcance estricto del ticket) — Alcance del programa de fondo de ahorro

Se levanta aquí para visibilidad; **no bloquea el cierre del ticket 14456**.

1. **Los aportes solo están cableados en la estructura 37 "Nómina Empleados"** (`EMP_FA` id 10811 y `PAT_FA` id 10812). Las estructuras 38 "Nómina Ejecutiva" (264 recibos), 39 "Nómina Obreros" (6.453 recibos) y 40 "Ayuda Semanal" (12.197 recibos) no aportan al fondo. Las reglas antiguas `INCENTIVO` (estructura 39) e `INCENTIVO2` (estructura 37) están **archivadas**. Confirmar con el cliente si esto es intencional o si falta configuración.
2. **Solo INDUVAR tiene el programa configurado**: 71 fondos y 2 porcentajes (5 % y 10 %), todos de la compañía 1. SAVONE, TEC ENVASE, JABONERÍA CARACAS y BERSA-CHEM tienen estructuras y recibos activos pero **0 fondos y 0 porcentajes**. Confirmar si el beneficio aplica solo a INDUVAR.

---

## 6. Procedimiento operativo del retiro total, una vez configurado

Para el analista de nómina. Las etiquetas son las que ve en INDUVAR.

1. **Nómina → Incentivo al Ahorro → Movimientos → Nuevo.**
2. **Incentivo al Ahorro:** seleccionar el fondo del trabajador (solo aparecen los activos).
3. **Tipo de movimiento:** `Retiro Total IA`. El campo **Monto** se autocompleta con el capital del fondo. No modificarlo: al confirmar, el sistema lo vuelve a fijar con el capital vigente en ese momento.
4. **Fecha:** debe ser **menor o igual** a la fecha "hasta" del recibo donde se va a pagar. Si es posterior, el módulo no la recoge (`date <= self.date_to`).
5. Marcar **Pagar por Nómina**.
6. Pulsar **Confirmar**. Verificar de inmediato:
   - Se creó una línea en el fondo de tipo "Retiro Total IA" con monto **negativo**.
   - El **Capital** del fondo quedó en **0,00**.
   - El **Estado de Pago** del movimiento es **Pendiente**.
7. Ir al recibo de **Liquidación** del trabajador (estructura 47) y pulsar **Calcular Hoja**.
8. En la pestaña **Otras Entradas** debe aparecer una línea de tipo `PAGO_FA` con el monto del retiro. Si no aparece, la regla del Paso 1 no está bien configurada o la fecha del movimiento es posterior al período.
9. Verificar que la línea del recibo con la regla del pago existe y que el **neto** subió en ese monto.
10. **Confirmar** el recibo. El movimiento pasa a **Pagado** y queda enlazado en el campo "Pagado en Recibo".
11. Si hay que corregir: **cancelar** el recibo devuelve el movimiento a **Pendiente** (devolverlo a borrador **no** lo libera).

**Restricciones a tener presentes:**

- No se puede confirmar un retiro sobre un fondo inactivo (`action_confirm` lo bloquea con "The Savings Fund of ... is inactive").
- No se puede desactivar un fondo con movimientos confirmados pendientes de pago por nómina (`_get_deactivation_blockers`, `hr_savings_fund.py:134`).
- Un movimiento confirmado **no se puede cancelar**; hay que registrar un movimiento de ajuste (`action_cancel`, línea 305).

---

## 7. Pruebas de aceptación

Ejecutar sobre un trabajador de prueba en `17_idv_stg` con fondo activo y capital > 0, después de aplicar los pasos 1 a 4.

| # | Verificación | Resultado esperado |
|---:|---|---|
| 1 | Al elegir tipo "Retiro Total IA", el campo Monto | Se autocompleta con el capital exacto del fondo |
| 2 | Al confirmar el movimiento, líneas del fondo | Aparece **una** línea nueva de tipo "Retiro Total IA" con importe **negativo** igual al capital previo |
| 3 | Capital del fondo tras confirmar | **0,00** |
| 4 | Estado de Pago del movimiento | **Pendiente** |
| 5 | Al calcular el recibo de Liquidación, pestaña Otras Entradas | **Una sola** línea de tipo `PAGO_FA` con monto **igual al capital retirado** (no dos; si aparecen dos, el Paso 2 o el Paso 3 no se aplicaron) |
| 6 | Línea del recibo de la regla del Paso 1 | Existe, con el mismo monto |
| 7 | Neto del recibo | Sube **exactamente** el monto del retiro respecto a un recibo idéntico sin el movimiento. Si la línea aparece pero el neto no cambia, la categoría no está recogida por la regla `NET` — volver a la nota crítica del Paso 1 |
| 8 | Al confirmar el recibo, estado del movimiento | **Pagado**, con el recibo enlazado en "Pagado en Recibo" |
| 9 | Al cancelar el recibo, estado del movimiento | Vuelve a **Pendiente** y el enlace al recibo se limpia |
| 10 | Recalcular el recibo dos veces seguidas | Sigue habiendo **una sola** otra entrada `PAGO_FA` (el módulo borra la anterior antes de inyectar) |
| 11 | Con un retiro parcial y un retiro total pendientes a la vez | **Una sola** otra entrada `PAGO_FA` con la **suma** de ambos, y al confirmar el recibo **ambos** movimientos quedan Pagados |
| 12 | Movimiento con fecha posterior al `date_to` del recibo | **No** genera otra entrada |
| 13 | Movimiento en borrador, o confirmado sin "Pagar por Nómina" | **No** genera otra entrada |
| 14 | Intentar crear una segunda regla con el check en la estructura 47 | Odoo lo rechaza: *"There can only be one Advance Payments - Savings Fund rule per structure"* |
| 15 | Intentar desactivar el fondo con el retiro confirmado y aún no pagado | Odoo lo rechaza con el listado de movimientos pendientes |

---

## 8. Riesgos: por qué NO implementar el check tal como lo pide el ticket

Añadir un check "Retiro Total" al tipo de otra entrada —es decir, que el analista capture a mano una otra entrada marcada como retiro total y que el sistema reaccione desde el recibo— **degradaría** el diseño actual:

| Riesgo | Detalle |
|---|---|
| **Segunda vía que se salta los guards** | Todas las validaciones viven en `hr_savings_fund_movement.py::action_confirm` (línea 197): fondo activo, movimiento en borrador, monto > 0, monto ≤ capital disponible, manejo de tasa y bimoneda. Una entrada capturada en el recibo no pasa por ninguna de ellas. Se podría pagar un retiro total de un fondo inactivo o por un monto superior al capital. |
| **Débito duplicado del capital** | El módulo ya crea la `hr.savings.fund.line` negativa al confirmar el movimiento. Si además se creara una línea desde el recibo, el capital se debitaría **dos veces** y quedaría negativo. Y si no se creara, el ticket no se cumple: no se alimentarían las líneas ni se debitaría el capital. |
| **Rompe el seguimiento del pago** | `payment_state` (`hr_savings_fund_movement.py:98`) y `_register_savings_fund_advance_payments` (`hr_payslip.py:167`) se apoyan en `payment_payslip_id`. Un pago nacido en el recibo no tendría movimiento al que enlazarse: no habría trazabilidad Pendiente → Pagado ni reversión al cancelar. |
| **Rompe el cierre del fondo** | `_get_deactivation_blockers` (`hr_savings_fund.py:134`) impide desactivar un fondo con pagos pendientes buscando movimientos. Sin movimiento, el fondo se podría cerrar con un pago en curso. |
| **Colisión de códigos** | Un tipo de entrada nuevo con código propio obligaría a una segunda regla, y si se reutilizara `PAGO_FA` reproduciría exactamente el problema del registro 221 (montos sumados, pago doble). |
| **Doble mantenimiento** | Dos caminos que hacen lo mismo, uno validado y otro no. En el primer descuadre, nadie sabrá cuál es la fuente de verdad. |

**El check que pide el ticket ya existe** (`is_savings_fund_advance_payment` en `hr.payslip.input.type`, registro id 215) y **ya cubre el retiro total**, porque `_get_savings_fund_movements_to_pay` (`hr_payslip.py:112`) excluye únicamente `loan_amortization`. Lo que falta es la regla del Paso 1.

---

## 9. Excepción legítima: cuándo sí haría falta desarrollo

Existe un escenario que sí justifica código, y conviene confirmarlo antes de cerrar el ticket:

> **Pregunta al analista funcional:** ¿el cliente necesita que el **retiro total** aparezca en el recibo como un **concepto separado** del retiro parcial —línea propia, código propio, con tratamiento contable o de ARC distinto— o le basta con que el monto se pague, se refleje en el fondo y debite el capital (que es lo que ya hace el módulo)?

Si la respuesta es "concepto separado", el desarrollo es acotado:

1. Un segundo campo booleano en `hr.salary.rule` y en `hr.payslip.input.type` (por ejemplo `is_savings_fund_total_withdrawal`).
2. Un tipo de otra entrada nuevo con código propio (por ejemplo `RETIRO_FA`), instalado por el módulo.
3. Partir `_update_savings_fund_advance_inputs` (`hr_payslip.py:135`) para agrupar los movimientos pendientes **por tipo** e inyectar una otra entrada por grupo, en vez de una sola con la suma.
4. Partir `_register_savings_fund_advance_payments` (`hr_payslip.py:167`) de forma simétrica: consumir cada grupo contra el total pagado por su propia regla.
5. Ampliar `_check_savings_fund_contribution_per_structure` (`hr_salary_rule.py:25`) con el nuevo flag.
6. Extender `tests/test_savings_fund_payslip.py` con los casos de convivencia (retiro parcial y total pendientes simultáneamente).

**Estimación: medio día de desarrollo más pruebas.** Sigue siendo una extensión del mecanismo existente, no una segunda vía paralela.

Si la respuesta es "basta con que se pague", **el ticket se cierra con la configuración de la sección 5**.

---

## 10. Limitación conocida (a levantar como incidencia aparte)

**En una liquidación, el retiro total no arrastra los aportes generados por ese mismo recibo.**

Causa, verificada en el código:

| Momento | Método | Qué ocurre |
|---|---|---|
| Al **calcular** el recibo | `compute_sheet` (`hr_payslip.py:23`) → `_update_savings_fund_advance_inputs` (línea 135) | La otra entrada `PAGO_FA` se fija con el capital **en ese instante** |
| Al **confirmar** el recibo | `action_payslip_done` (línea 8) → `_register_savings_fund_contributions` (línea 63) | Los aportes `EMP_FA` y `PAT_FA` de **ese** recibo se acreditan al fondo, **después** |

Es decir: si se confirma el retiro total antes de calcular la liquidación, el monto pagado será el capital **sin** los aportes de ese último recibo. Esos aportes ingresan al fondo al confirmarlo, y el trabajador queda con un saldo residual que exige un **segundo retiro total** y, por tanto, un segundo recibo.

**Ningún check en las otras entradas resuelve esto**, porque el problema es de orden temporal, no de detección. Las salidas posibles:

- **Procedimiento (inmediato, sin código):** ejecutar la liquidación en dos pasos —confirmar el recibo de liquidación primero, y solo después crear y confirmar el retiro total, pagándolo en un recibo de la estructura 141. Es el esquema que INDUVAR ya usa para los retiros parciales.
- **Desarrollo (a evaluar aparte):** recalcular la otra entrada `PAGO_FA` dentro de `action_payslip_done`, después de registrar los aportes, cuando la estructura sea de liquidación. Implica reordenar el flujo y tiene efectos secundarios sobre el neto ya confirmado; requiere análisis propio.

Se recomienda **abrir un ticket independiente** para esta limitación y no mezclarla con el 14456.

---

## 11. Resumen de acciones

| # | Acción | Objeto | Responsable | Bloquea el cierre |
|---:|---|---|---|:---:|
| 0 | Restaurar los módulos en `src/custom/idv` y actualizar la instancia | `binaural_hr_savings_fund`, `induvar_hr_savings_fund` | Técnico / DevOps | **Sí** |
| 1 | Crear la regla con el check "Pago Anticipos", categoría `ALW` | Estructura 47 | Funcional | **Sí** |
| 2 | Archivar la regla manual y su tipo de entrada | Regla 1848, tipo 94 | Funcional | **Sí** |
| 3 | Eliminar el tipo de entrada duplicado | Tipo 221 | Funcional | **Sí** |
| 4 | Eliminar el tipo de entrada muerto | Tipo 220 (y regla inactiva 10817) | Funcional | No |
| 5 | Decidir el alcance: recibo dedicado o nómina regular | Estructuras 37/38/39/40 | Funcional + cliente | **Sí** (decisión) |
| 6 | Confirmar la pregunta de la sección 9 | — | Funcional + cliente | **Sí** (decisión) |
| 7 | Ejecutar las 15 pruebas de aceptación | Base `17_idv_stg` | Funcional | **Sí** |
| 8 | Levantar el alcance del programa (aportes y compañías) | — | Funcional | No |
| 9 | Levantar la limitación de la sección 10 como ticket aparte | — | Técnico | No |

---

### Referencias de código

Todas las rutas relativas a `src/integra-addons/binaural_hr_savings_fund/` salvo indicación contraria. **Los números de línea están fijados a `origin/l10nve_17.0`**, que es la referencia estable. Al momento de redactar este documento hay trabajo en curso sobre `models/hr_savings_fund_movement.py`, `tests/test_savings_fund_movement.py` y `views/hr_savings_fund_movement_views.xml` en una rama local, por lo que en un árbol de trabajo esas líneas pueden estar desplazadas. Los archivos citados con más peso en este análisis —`hr_payslip.py`, `hr_salary_rule.py`, `hr_savings_fund.py` y `hr_payslip_input_type.py`— no están afectados.

| Referencia | Ubicación |
|---|---|
| Tipo de otra entrada `PAGO_FA` | `data/hr_payslip_input_type_data.xml` |
| Check en el tipo de entrada | `models/hr_payslip_input_type.py:7` |
| Check en la regla salarial | `models/hr_salary_rule.py:18` |
| Validación de una sola regla por estructura | `models/hr_salary_rule.py:25-77` |
| Selección de movimientos a pagar | `models/hr_payslip.py:112` |
| Inyección de la otra entrada | `models/hr_payslip.py:135` (guard en 150-152) |
| Conciliación del pago | `models/hr_payslip.py:167` |
| Liberación al cancelar el recibo | `models/hr_payslip.py:16` |
| Registro de aportes | `models/hr_payslip.py:63` |
| Confirmación del movimiento y línea del fondo | `models/hr_savings_fund_movement.py:197` (línea del fondo en 241-253) |
| Autocompletado del monto del retiro total | `models/hr_savings_fund_movement.py:171` |
| Cálculo del capital | `models/hr_savings_fund.py:114` |
| Bloqueos de desactivación | `models/hr_savings_fund.py:134` |
| Diccionario `inputs` indexado por código | `src/enterprise-17/hr_payroll/models/hr_payslip.py:799-828` |
| Agregador que suma códigos repetidos | `src/enterprise-17/hr_payroll/models/hr_payslip.py:1438-1442` |
| Protección de borrado de tipos con XML ID | `src/enterprise-17/hr_payroll/models/hr_payslip_input_type.py:18-24` |
| Restricciones de INDUVAR | `src/custom/idv/induvar_hr_savings_fund/models/hr_savings_fund_movement.py` |

*Documento generado el 05/08/2026 a partir del código en la rama `l10nve_17.0` y de consultas de solo lectura sobre la base `17_idv_stg`.*
