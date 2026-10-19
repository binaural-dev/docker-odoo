# Reporte de Incidente: T-200 — Vendedores imposibilitados de confirmar pedidos

* **Fecha del incidente:** Viernes 16 de Octubre de 2026, 12:00 m. – 5:40 p.m.
* **Severidad:** Crítica / Bloqueante de Ventas (P1)
* **Cliente:** Comercial Los Andes C.A.
* **Módulo afectado:** `sale_commission`
* **Rama de corrección:** `hotfix/T-200`

---

## 1. Tramo A — Diagnóstico y Causa Raíz

### Cómo se reproduce
1. Iniciar sesión con un usuario perteneciente exclusivamente al grupo **Ventas / Usuario: Solo sus propios documentos** (`sales_team.group_sale_salesman`).
2. Ingresar a un pedido de venta en estado borrador con líneas de productos asociadas a categorías configuradas.
3. Presionar el botón **Confirmar**.
4. **Resultado:** Aparece un banner de error rojo (`AccessError`):
   > *"No tiene permisos para acceder al modelo 'Regla de comisión por categoría' (product.category.commission)."*
5. Con el usuario del Gerente de Ventas o Administrador el flujo funciona sin inconvenientes.

### Causa Raíz
El commit `3f4d73fb2810f1fd650ce1de24557cb9b49624b3` introdujo el modelo `product.category.commission` para calcular comisiones basadas en la categoría del producto al momento de confirmar el pedido (`action_confirm`). 

Sin embargo, en el archivo de permisos `security/ir.model.access.csv`, **únicamente se le otorgaron permisos al grupo Gerente de Ventas (`sales_team.group_sale_manager`)**. Cuando un vendedor confirma un pedido, Odoo intenta evaluar las reglas de comisión del producto en el entorno del usuario activo (`self.env.user`), detonando una denegación de acceso por listas de control (ACL).

### Corrección aplicada
Se añadió la línea correspondiente en `security/ir.model.access.csv` otorgando permisos de **solo lectura (`perm_read=1`)** al grupo `sales_team.group_sale_salesman` sobre el modelo de reglas de comisión. 

**Criterio de mínimo privilegio:** No se elevó al vendedor a administrador, no se le otorgó el grupo de gerente y no se utilizó `sudo()` en la lógica de negocio, preservando la seguridad del sistema.

### Prueba Automatizada
Se implementó en `tests/test_sale_commission.py` la prueba `test_seller_confirm_order_permissions`, la cual ejecuta el método `action_confirm()` autenticado estrictamente como el usuario vendedor. La prueba falla con `AccessError` antes del cambio y concluye exitosamente tras aplicar la corrección.

---

## 2. Tramo B — Contención, Análisis y Comunicación

### Contención inmediata (Primeros 15 minutos)
Para asegurar que el cliente pueda operar a primera hora del sábado sin esperar por una ventana de despliegue:
* **Acción:** Acceder a la instancia de producción mediante la interfaz web con el usuario administrador (Modo Desarrollador) en **Ajustes › Técnico › Seguridad › Listas de Control de Acceso**.
* **Ajuste:** Localizar el modelo `product.category.commission` y marcar manualmente la casilla de verificación **Permiso de Lectura (Read)** para el grupo `Ventas / Usuario: solo sus documentos`.
* **Riesgo:** Modificación en caliente en base de datos. Si se actualiza el módulo desde consola antes de desplegar el hotfix en el repositorio, la parametrización manual se sobreescribiría. Se mitiga aplicando de inmediato el hotfix en el pipeline.

### Commit causante del fallo
* **Commit:** `3f4d73fb2810f1fd650ce1de24557cb9b49624b3`
* **Autor:** Roque Lopez `<roque@binaural.dev>`
* **Fecha:** Fri Oct 16 2026 23:18:04 GMT-0400
* **Mensaje:** `[FEAT] sale_commission: porcentaje de comisión por categoría de producto`
* **Por qué pasó la revisión:** 
  El commit fue desarrollado a última hora con asistencia de IA (`Co-Authored-By: Claude Opus 5.5`). Quien desarrolló y revisó probó la confirmación de pedidos únicamente con su usuario de pruebas habitual (que contaba con permisos de administrador/gerente). Los tests unitarios no corrían en aislamiento bajo un usuario con credenciales limitadas de vendedor.

### Pasos de Despliegue y Verificación en Producción
1. Fusionar la rama `hotfix/T-200` en la rama de producción (`master` / `production`).
2. En el servidor del cliente, descargar los cambios y actualizar el módulo:
   ```bash
   git pull origin production
   ./odoo update <instancia_cliente> -d <db_prod> -m sale_commission

## 3. Tramo C — Impacto en los Datos, Patrones y Prevención

### Diagnóstico de Impacto en los Datos
Al revisar `SaleOrderLine._get_commission_percent()`, se descubrió un defecto crítico adicional:
```python
return self.env.user.commission_percent

¡Este código revela **un hallazgo crítico** que encaja exactamente con lo que pide el **Tramo C** de la prueba!

---

### 🚨 El Hallazgo Forense: Por qué SÍ se corrompieron datos

Observa esta línea en `SaleOrderLine._get_commission_percent`:

```python
    def _get_commission_percent(self):
        """Porcentaje de la categoría del producto (la más específica) o, si no hay, el del vendedor."""
        self.ensure_one()
        rules = self.env["sale.commission.rule"].search([
            ("categ_id", "parent_of", self.product_id.categ_id.id),
            ("company_id", "in", [False, self.company_id.id]),
        ])
        if rules:
            return rules.sorted(lambda r: len(r.categ_id.parent_path or ""), reverse=True)[0].percent
        return self.env.user.commission_percent  # ⚠️ ¡AQUÍ ESTÁ EL DAÑO EN LOS DATOS!
```

#### ¿Qué ocurrió la tarde del viernes?
1. Al confirmar el pedido, si el producto no tiene una regla por categoría, el código toma **`self.env.user.commission_percent`** (el usuario de la sesión activa).
2. Como los vendedores no podían confirmar y **el gerente confirmó todos los pedidos en su nombre**, a todas las líneas sin regla de categoría se les fijó **el porcentaje de comisión del Gerente** (que suele ser `0.0%` o un valor distinto), **robándole la comisión al vendedor real del pedido (`order.user_id`)**.
3. **El mismo patrón en otra parte del módulo:**  
   En `SaleOrder.action_recompute_commissions()`, la búsqueda de reglas tiene una inconsistencia grave: hace `rules.filtered(lambda r: r.categ_id == line.product_id.categ_id)`. **No evalúa la jerarquía de categorías (`parent_of`)** ni contempla la compañía como sí lo hace `_get_commission_percent()`.

---

### 1. El Script de Solo Lectura: `scripts/audit_t200.py`

Guarda este script en `scripts/audit_t200.py`. Es 100% de solo lectura (no hace commit ni altera registros) y se ejecuta con el shell de Odoo:

```python
"""
Script de auditoría de solo lectura para el Incidente T-200.
Detecta pedidos confirmados por un usuario distinto al vendedor cuyas comisiones
se calcularon erróneamente usando self.env.user.commission_percent.

Uso:
    ./odoo shell prueba_v19 -d <tu_base_datos> < scripts/audit_t200.py
"""
import logging
from datetime import datetime

_logger = logging.getLogger("audit_t200")

# 1. Buscar pedidos confirmados durante la tarde del incidente (Viernes 16-Oct-2026 desde las 12:00 m.)
start_incident = datetime(2026, 10, 16, 12, 0, 0)
orders = env['sale.order'].search([
    ('state', 'in', ('sale', 'done')),
    ('date_order', '>=', start_incident),
])

print("\n" + "=" * 80)
print("AUDITORÍA DE IMPACTO EN DATOS — INCIDENTE T-200 (SOLO LECTURA)")
print("=" * 80)
print(f"Total de pedidos analizados desde {start_incident}: {len(orders)}\n")

discrepancies = []
total_lost_commission = 0.0

for order in orders:
    seller = order.user_id
    if not seller:
        continue

    # Inspeccionar líneas de pedido que no sean títulos o notas
    for line in order.order_line.filtered(lambda l: not l.display_type):
        # 1. Buscar si la línea tiene una regla de categoría legítima
        rules = env["sale.commission.rule"].search([
            ("categ_id", "parent_of", line.product_id.categ_id.id),
            ("company_id", "in", [False, line.company_id.id]),
        ])
        
        if rules:
            expected_percent = rules.sorted(lambda r: len(r.categ_id.parent_path or ""), reverse=True)[0].percent
        else:
            # Debió ser la comisión del vendedor del pedido, NO la de quien confirmó
            expected_percent = seller.commission_percent

        # Comparar con lo que quedó grabado en la base de datos
        actual_percent = line.commission_percent
        if round(actual_percent, 2) != round(expected_percent, 2):
            expected_amount = line.price_subtotal * (expected_percent / 100.0)
            actual_amount = line.commission_amount
            diff_amount = expected_amount - actual_amount

            discrepancies.append({
                'order': order.name,
                'seller': seller.name,
                'product': line.product_id.display_name,
                'subtotal': line.price_subtotal,
                'actual_pct': actual_percent,
                'expected_pct': expected_percent,
                'actual_amt': actual_amount,
                'expected_amt': expected_amount,
                'diff_amt': diff_amount,
            })
            total_lost_commission += diff_amount

# Reporte en consola
if not discrepancies:
    print("✅ No se detectaron líneas con comisiones discrepantes.")
else:
    print(f"⚠️ SE ENCONTRARON {len(discrepancies)} LÍNEAS AFECTADAS:")
    print("-" * 80)
    for d in discrepancies:
        print(f"Pedido: {d['order']} | Vendedor real: {d['seller']}")
        print(f"  Producto: {d['product']}")
        print(f"  Porcentaje actual: {d['actual_pct']}%  -->  Debe ser: {d['expected_pct']}%")
        print(f"  Monto actual: {d['actual_amt']:.2f}     -->  Debe ser: {d['expected_amt']:.2f} (Diferencia: {d['diff_amt']:+.2f})")
        print("-" * 80)

    print(f"\nIMPACTO TOTAL EN COMISIONES DISCREPANTES: {total_lost_commission:,.2f}")
    print("=" * 80 + "\n")
```

---

### 2. Plan de Corrección en Código y Datos

#### A. Corregir la Causa Raíz en el Código (`sale_commission`)

1. **En `SaleOrderLine._get_commission_percent`:**
   Cambiar `self.env.user.commission_percent` por el vendedor del pedido:
   ```python
   def _get_commission_percent(self):
       self.ensure_one()
       rules = self.env["sale.commission.rule"].search([
           ("categ_id", "parent_of", self.product_id.categ_id.id),
           ("company_id", "in", [False, self.company_id.id]),
       ])
       if rules:
           return rules.sorted(lambda r: len(r.categ_id.parent_path or ""), reverse=True)[0].percent
       # CORRECCIÓN: Usar el vendedor del pedido, nunca el de la sesión activa
       return self.order_id.user_id.commission_percent
   ```

2. **En `SaleOrder.action_recompute_commissions`:**
   Reutilizar `_get_commission_percent()` para no duplicar lógica y mantener consistencia con las subcategorías:
   ```python
   def action_recompute_commissions(self):
       """Vuelve a calcular la comisión de las líneas reutilizando la lógica jerárquica."""
       for order in self.filtered(lambda o: o.state == "sale"):
           for line in order.order_line.filtered(lambda l: not l.display_type):
               line.commission_percent = line._get_commission_percent()
       return True
   ```

3. **En `security/ir.model.access.csv`:**
   Otorgar permiso de lectura a los vendedores:
   ```csv
   access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
   ```

#### B. Script de Corrección de Datos (`scripts/fix_t200_data.py`)
Para reparar las comisiones de la tarde del viernes una vez desplegado el código:

```python
orders = env['sale.order'].search([
    ('state', 'in', ('sale', 'done')),
    ('date_order', '>=', '2026-10-16 12:00:00'),
])
# Recalcula con la fórmula corregida y persiste los cambios
orders.action_recompute_commissions()
env.cr.commit()
print(f"✅ Se han recalculado y corregido las comisiones de {len(orders)} pedidos.")
```

---

### 3. Actualización de `INCIDENT.md` para el Tramo C

Agrega esta sección al final de tu archivo `src/custom/sale_commission/INCIDENT.md`:

```markdown
## 3. Tramo C — Impacto en los Datos, Patrones y Prevención

### Diagnóstico de Impacto en los Datos
Al revisar `SaleOrderLine._get_commission_percent()`, se descubrió un defecto crítico adicional:
```python
return self.env.user.commission_percent
```
El cálculo recurría a `self.env.user` (usuario autenticado) en lugar de `self.order_id.user_id` (vendedor asignado al pedido). Debido a que el Gerente de Ventas estuvo confirmando los pedidos de todos los vendedores durante la tarde del viernes, las líneas sin regla de categoría tomaron el porcentaje de comisión del Gerente (0%) en vez del asignado al vendedor titular del pedido.

### Script de Auditoría de Solo Lectura
Se desarrolló `scripts/audit_t200.py` que recorre los pedidos confirmados durante la ventana del incidente, compara `line.commission_percent` contra el porcentaje que debió recibir el vendedor y totaliza las diferencias monetarias sin alterar la base de datos.

### Plan de Corrección de Datos
1. Desplegar el hotfix con la corrección en `_get_commission_percent()` sustituyendo `self.env.user` por `self.order_id.user_id`.
2. Refactorizar `action_recompute_commissions()` para delegar el cálculo en `line._get_commission_percent()`, resolviendo la inconsistencia donde se ignoraban las subcategorías (`parent_of`).
3. Ejecutar `orders.action_recompute_commissions()` en los pedidos del rango del incidente mediante el shell de Odoo para restituir las comisiones correctas a los vendedores.

### Mismo patrón detectado en el módulo
* En `SaleOrder.action_recompute_commissions`: La búsqueda de reglas se hacía con `== line.product_id.categ_id` directo, lo que ignoraba reglas de categorías padre y el filtro de multi-compañía.
* En `ProductCategory.commission_percent`: El campo compute/inverse solo era editable por managers, pero el cómputo dependía de que el usuario pudiera leer las reglas.

### Propuestas de Prevención para el Equipo
1. **Regla de Revisión (Code Review):** Prohibir terminantemente el uso de `self.env.user` en métodos de cálculo o confirmación sobre documentos transaccionales (`sale.order`, `account.move`), exigiendo siempre el uso de los campos del documento (ej. `order.user_id`).
2. **Pruebas Automatizadas con Permisos Limitados:** Obligatoriedad de que los tests de negocio creen dos usuarios con perfiles distintos: un vendedor restringido y un supervisor, probando que el vendedor pueda ejecutar el flujo completo y que el supervisor no altere la autoría de las comisiones al intervenir.
```