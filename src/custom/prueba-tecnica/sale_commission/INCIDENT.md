# INCIDENT — T-200 · Crítica · «¡No podemos vender!»

| | |
|---|---|
| Cliente | Comercial Los Andes C.A. (ficticia) |
| Módulo | `sale_commission` (1.1.0 → **1.1.1**) |
| Síntoma | Desde el despliegue de las 12:00 m., ningún vendedor puede confirmar pedidos (error rojo). El gerente sí puede. |
| Rama | `hotfix/T-200` |
| Commits | `9a95e9d` [TEST] prueba que reproduce · `3dbd7a3` [FIX] corrección |

## 1. Cómo se reproduce

**En la interfaz**

1. Con un usuario que solo tenga *Ventas › Usuario: solo sus documentos* (`sales_team.group_sale_salesman`),
   crear una cotización propia con cualquier producto.
2. Pulsar **Confirmar**.
3. Aparece el error:

   ```
   You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
   This operation is allowed for the following groups:
       - Sales/Administrator
   ```

4. La misma cotización, confirmada por un usuario *Ventas › Administrador*, se confirma sin problema.

**En las pruebas** (corren con el usuario vendedor, no como administrador):

```bash
./odoo test prueba-tecnica sale_commission -d t200
```

Antes de la corrección (`9a95e9d`): `0 failed, 2 error(s) of 8 tests`. Fallan
`test_t200_salesman_confirms_own_order` y `test_t200_salesman_confirm_uses_category_rule` con:

```
File ".../sale_commission/models/sale_order.py", line 10, in action_confirm
    line.commission_percent = line._get_commission_percent()
File ".../sale_commission/models/sale_order_line.py", line 28, in _get_commission_percent
    rules = self.env["sale.commission.rule"].search([
...
odoo.exceptions.AccessError: You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
```

## 2. Causa raíz

La actualización desplegada a las 12:00 m. (commit `3f4d73f`, «porcentaje de comisión por categoría de
producto») creó el modelo `sale.commission.rule` y cambió cómo se fija la comisión:

- `sale.order.action_confirm()` ahora llama a `sale.order.line._get_commission_percent()`, que hace un
  `search()` sobre `sale.commission.rule` **con el usuario que confirma**.
- En `security/ir.model.access.csv` el modelo nuevo solo recibió acceso para
  `sales_team.group_sale_manager`. Un vendedor no tiene ni lectura, así que el `search()` lanza
  `AccessError` y toda la confirmación se revierte.
- El gerente sí tiene acceso; por eso «con el usuario del gerente funciona».

No es un problema de datos ni de configuración del cliente: es un permiso que faltó en el código.

## 3. Corrección

Una línea en `security/ir.model.access.csv`:

```csv
access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
```

- **Solo lectura** para el vendedor: puede leer los porcentajes que el sistema necesita para calcular su
  comisión, pero no puede crear, modificar ni borrar reglas (lo cubre una prueba).
- **Sin `sudo()`** y sin darle al vendedor el grupo del gerente. Se descartó `sudo()` en
  `_get_commission_percent()` porque esconde el problema en vez de declarar quién puede leer qué, y cualquier
  otra lectura de reglas (por ejemplo `action_recompute_commissions`) seguiría fallando.
- Que el vendedor pueda leer los porcentajes por categoría es aceptable: son las condiciones de su propia
  comisión. Si el cliente quisiera ocultarlos, habría que mover el cálculo a un método con `sudo()`
  justificado y documentado; queda como pregunta para el cliente, no para el hotfix.
- Se sube la versión a `1.1.1` para que la actualización quede registrada.

No se tocó la lógica del módulo: es producción y el cambio mínimo es el que menos riesgo tiene.

## 4. Pruebas

Nuevas en `tests/test_sale_commission.py`, todas con `with_user()`:

| Prueba | Qué demuestra | Antes | Después |
|---|---|---|---|
| `test_t200_salesman_confirms_own_order` | El vendedor crea y confirma su pedido; la comisión es la suya (5 %) | ❌ AccessError | ✅ |
| `test_t200_salesman_confirm_uses_category_rule` | Como vendedor, se aplica la regla de la categoría (8 %) | ❌ AccessError | ✅ |
| `test_t200_manager_still_confirms` | El gerente sigue confirmando pedidos de un vendedor | ✅ | ✅ |
| `test_t200_salesman_cannot_manage_rules` | El vendedor **no** puede modificar, crear ni borrar reglas | ✅ | ✅ |

Después de la corrección (`3dbd7a3`): `0 failed, 0 error(s) of 8 tests`.

## 5. Contención, despliegue y comunicación (tramo B)

Pendiente.

## 6. Impacto en los datos y prevención (tramo C)

Pendiente. Hallazgo anotado para este tramo: en el mismo commit, `_get_commission_percent()` usa como
respaldo `self.env.user.commission_percent` (el porcentaje de **quien confirma**) en lugar del vendedor del
pedido. Los pedidos que el gerente confirmó esta tarde pueden haber quedado con el porcentaje del gerente.
