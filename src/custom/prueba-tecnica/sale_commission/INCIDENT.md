# Reporte de Incidente T-200 — Módulo sale_commission

**Fecha del incidente:** Viernes, 2026-Q4, 17:40  
**Cliente afectado:** Comercial Los Andes C.A.  
**Severidad:** Crítica (Bloqueo total del flujo de ventas para vendedores)  
**Estado:** Resuelto en rama `hotfix/T-200`

---

## Tramo A — Diagnóstico, Causa Raíz y Corrección

### 1. Reproducción del Error
1. Iniciar sesión en Odoo con un usuario perteneciente exclusivamente al grupo de vendedores: **`sales_team.group_sale_salesman`** (*Ventas / Mostrar solo documentos propios*).
2. Crear o abrir una cotización de venta en estado borrador (`draft`).
3. Hacer clic en el botón **"Confirmar"** (`action_confirm`).
4. **Resultado observado:** Odoo interrumpe la transacción y despliega un diálogo de error de acceso:
   ```text
   odoo.exceptions.AccessError: No tiene los permisos necesarios para acceder a 'Comisión por categoría de producto' (sale.commission.rule).
   Operación: read
   Grupos del usuario: Ventas / Mostrar solo documentos propios
   ```

### 2. Causa Raíz Técnica
Al ejecutar `action_confirm()` en la orden de venta, el método sobreescrito en `models/sale_order.py` itera las líneas del pedido y ejecuta `line._get_commission_percent()`.
En `models/sale_order_line.py`:
```python
rules = self.env["sale.commission.rule"].search([
    ("categ_id", "parent_of", self.product_id.categ_id.id),
    ("company_id", "in", [False, self.company_id.id]),
])
```
* En el archivo de control de acceso `security/ir.model.access.csv`, el modelo `model_sale_commission_rule` únicamente contaba con la entrada:
  `access_sale_commission_rule_manager,sale.commission.rule.manager,model_sale_commission_rule,sales_team.group_sale_manager,1,1,1,1`
* El grupo de vendedores (`sales_team.group_sale_salesman`) no poseía ningún registro de permisos sobre el modelo `sale.commission.rule`. Por política por defecto de Odoo, cualquier acceso no declarado es denegado, disparando la excepción `AccessError`.
* El usuario gerente sí podía confirmar porque pertenece a `sales_team.group_sale_manager`, que tiene permisos completos (`1,1,1,1`).

Adicionalmente, se detectó una segunda causa raíz crítica en la línea 34 de `sale_order_line.py`:
```python
return self.env.user.commission_percent
```
Tomaba el porcentaje del usuario actualmente autenticado en el entorno (`self.env.user`), en vez del vendedor asignado al pedido (`self.order_id.user_id`). Al confirmar el gerente pedidos ajenos, se sobreescribían los porcentajes con los del gerente.

### 3. Corrección Aplicada
Se aplicaron dos modificaciones quirúrgicas respetando el principio de mínimo privilegio y sin recurrir a `sudo()` injustificado:
1. **Permiso de lectura en `security/ir.model.access.csv`:**
   ```csv
   access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
   ```
   Se otorga exclusivamente permiso de lectura (`perm_read = 1`) al grupo de vendedores, impidiendo que creen (`perm_create = 0`), modifiquen (`perm_write = 0`) o eliminen (`perm_unlink = 0`) reglas de comisión.
2. **Corrección de referencia de vendedor en `models/sale_order_line.py`:**
   ```python
   return self.order_id.user_id.commission_percent if self.order_id.user_id else 0.0
   ```
   Se garantiza que la comisión calculada corresponda al vendedor del pedido (`order_id.user_id`), sin importar qué usuario detone la confirmación.

### 4. Prueba Automatizada
Se implementó en `tests/test_sale_commission.py`:
* `test_salesman_confirm_order_access`: Un usuario vendedor (`self.salesman`) ejecuta `order.with_user(self.salesman).action_confirm()`. Antes del fix falla con `AccessError`; después del fix la orden pasa a estado `sale` y calcula el monto exacto de comisión.
* `test_manager_confirming_salesman_order_keeps_salesman_commission`: Valida que si un gerente confirma el pedido de un vendedor, se preserve el porcentaje del vendedor (5%) y no el del gerente (15%).

---

## Tramo B — Contención, Investigación de Commit y Despliegue

### 1. Medidas de Contención Inmediata (Primeros 15 Minutos)
Para garantizar que el cliente pueda abrir el sábado a las 8:00 a.m. en caso de que un despliegue completo de código requiriera aprobaciones adicionales:
* **Acción de contención rápida:** 
  Ingresar a Odoo como Administrador en Modo Desarrollador → **Ajustes > Técnico > Seguridad > Listas de control de acceso**.
  Buscar el modelo `sale.commission.rule` y agregar manualmente una línea para el grupo **Ventas / Mostrar solo documentos propios** con permiso de **Lectura** activado.
* **Evaluación de riesgos:** 
  Riesgo mínimo y nulo impacto en integridad: solo otorga lectura sobre la tabla de reglas de porcentaje (que de todas formas es información comercial necesaria para liquidar la venta). No requiere reiniciar el servicio ni detiene la operación.

### 2. Identificación del Commit Culpable
* **Comando utilizado:** `git log -p -S "sale.commission.rule" -- src/custom/prueba-tecnica/sale_commission`
* **Commit causante:** `3f4d73f` (*"[FEAT] sale_commission: porcentaje de comisión por categoría de producto"*), desplegado hoy viernes a las 12:00 m.
* **¿Por qué pasó la revisión / CI?:**
  1. El desarrollador escribió los tests unitarios ejecutando `self._create_order()` con `self.env` (Superusuario/Admin) y llamando `order.action_confirm()` sin contexto de usuario (`with_user`), lo que omitió las verificaciones de seguridad de Odoo.
  2. En el test se agregó la línea artificial `cls.env.user.commission_percent = 5.0`, enmascarando que la función leía `self.env.user` en lugar del vendedor asignado al pedido.

### 3. Pasos de Despliegue y Verificación en Producción
1. Desplegar la rama `hotfix/T-200` en el servidor de producción.
2. Actualizar el módulo desde la línea de comandos de Odoo o con el CLI del repo:
   ```bash
   ./odoo update <instancia> sale_commission
   ```
3. **Verificación post-despliegue:**
   - Iniciar sesión con un usuario vendedor de pruebas.
   - Crear una cotización con un producto y confirmar. Verificar que la orden pase a "Pedido de Venta" y que el porcentaje de comisión coincida con el configurado en su perfil.
   - Iniciar sesión con el usuario gerente y verificar que también pueda confirmar pedidos normalmente.

### 4. Mensaje para el Cliente (3 a 5 líneas, sin jerga técnica)
> **Estimado equipo de Comercial Los Andes:**  
> Les confirmamos que hemos identificado y solucionado el inconveniente que impedía a los vendedores confirmar pedidos esta tarde. Aplicamos la corrección en el sistema y verificamos que el equipo de ventas ya puede operar con total normalidad para su jornada de mañana sábado. Además, revisaremos y ajustaremos cualquier cálculo de comisiones que se haya generado durante la tarde de hoy. Quedamos a su entera disposición ante cualquier duda.

---

## Tramo C — Auditoría de Datos Afectados y Prevención

### 1. Análisis de Impacto en los Datos
Durante la tarde (12:00 m. a 5:40 p.m.), el gerente confirmó pedidos en nombre de los vendedores. Dado que el código defectuoso ejecutaba:
`return self.env.user.commission_percent`
Todos los pedidos confirmados por el gerente cuyos productos no tenían una regla específica por categoría calcularon la comisión usando el porcentaje del **gerente** en lugar del porcentaje del **vendedor asignado al pedido**.

### 2. Script de Solo Lectura para Auditoría (Python / Odoo Shell)
El siguiente script identifica todos los pedidos y líneas confirmados hoy donde la comisión aplicada difiere de la comisión que le correspondía al vendedor:

```python
# Script de auditoría de solo lectura (ejecutar en odoo shell)
# No modifica ningún registro en la base de datos.

from datetime import date

orders_today = env["sale.order"].search([
    ("date_order", ">=", date.today().strftime("%Y-%m-%d 00:00:00")),
    ("state", "in", ["sale", "done"]),
])

affected_lines = []

for order in orders_today:
    expected_salesman_percent = order.user_id.commission_percent if order.user_id else 0.0
    for line in order.order_line.filtered(lambda l: not l.display_type):
        # Si la categoría no tiene regla específica, debió tomar la del vendedor
        rules = env["sale.commission.rule"].search([
            ("categ_id", "parent_of", line.product_id.categ_id.id),
            ("company_id", "in", [False, line.company_id.id]),
        ])
        if not rules and line.commission_percent != expected_salesman_percent:
            affected_lines.append({
                "order": order.name,
                "salesman": order.user_id.name,
                "product": line.product_id.name,
                "percent_applied": line.commission_percent,
                "percent_expected": expected_salesman_percent,
                "difference_amount": line.price_subtotal * (expected_salesman_percent - line.commission_percent) / 100.0,
            })

print(f"Total líneas afectadas detectadas: {len(affected_lines)}")
for item in affected_lines:
    print(f"Pedido: {item['order']} | Vendedor: {item['salesman']} | "
          f"Aplicado: {item['percent_applied']}% | Esperado: {item['percent_expected']}% | "
          f"Ajuste comisión: {item['difference_amount']:.2f}")
```

### 3. Plan de Corrección de Datos
1. Ejecutar el script de auditoría previo para obtener el respaldo del estado actual y los montos a corregir.
2. Utilizar el método ya existente en el modelo `sale.order`:
   `order.action_recompute_commissions()` sobre los pedidos confirmados el día de hoy.
3. Volver a ejecutar el script de auditoría para verificar que el número de líneas afectadas sea 0.
4. Notificar a Administración con el reporte consolidado de comisiones reajustadas.

### 4. Reglas de Prevención para el Equipo de Desarrollo
1. **Regla de pruebas de seguridad obligatoria:** Todo modelo nuevo o modificado que intervenga en flujos estándar de negocio debe contar con pruebas unitarias ejecutadas explícitamente con `with_user(test_user)`.
2. **Prohibición de `self.env.user` en lógica de documentos de negocio:** En modelos como `sale.order` o `sale.order.line`, la lógica nunca debe inferir atributos comerciales a partir de `self.env.user`; siempre debe referenciarse al campo relacional correspondiente (`order_id.user_id`).
3. **Checklist en PR template:** Agregar a la plantilla de Pull Requests la casilla obligatoria:
   - `[ ] Se definieron permisos en ir.model.access.csv para todos los grupos de usuario pertinentes (incluyendo solo lectura para perfiles operativos).`
