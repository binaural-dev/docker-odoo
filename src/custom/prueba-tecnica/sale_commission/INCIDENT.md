# Reporte de Incidente de Producción: Ticket T-200

**Cliente:** Comercial Los Andes C.A.  
**Severidad:** Crítica (P1 / Bloqueante de Ventas)  
**Módulo afectado:** `sale_commission`  
**Fecha y hora del reporte:** Viernes, 17:40  
**Fecha y hora del despliegue causante:** Viernes, 12:00 m.  
**Rama de corrección:** `hotfix/T-200`  

---

## Tramo A — Diagnóstico, Causa Raíz y Corrección

### 1. Reproducción del Error
1. Iniciar sesión con un usuario perteneciente al grupo de vendedores comerciales (`sales_team.group_sale_salesman`).
2. Crear un presupuesto o pedido de venta con al menos una línea de producto.
3. Hacer clic en el botón **Confirmar** (`action_confirm`).
4. **Resultado:** Se despliega un diálogo de error en color rojo bloqueando la confirmación:
   ```text
   Access Denied by ACLs for operation: read, uid: <salesman_id>, model: sale.commission.rule
   AccessError: You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
   This operation is allowed for the following groups:
       - Sales/Administrator
   ```
5. Si el mismo pedido es confirmado por un usuario con rol de Gerente de Ventas (`sales_team.group_sale_manager`), la confirmación no falla.

### 2. Causa Raíz
Se identificaron dos defectos concatenados introducidos en la versión 1.1.0 (commit `3f4d73f`):

1. **Permiso de lectura omitido en ACLs (`security/ir.model.access.csv`):**  
   Al introducir el modelo `sale.commission.rule`, únicamente se otorgaron permisos al grupo `sales_team.group_sale_manager`. Al confirmar pedidos, `models/sale_order_line.py` (`_get_commission_percent`) ejecuta una consulta ORM de búsqueda:
   ```python
   rules = self.env["sale.commission.rule"].search([
       ("categ_id", "parent_of", self.product_id.categ_id.id),
       ("company_id", "in", [False, self.company_id.id]),
   ])
   ```
   Al no poseer permisos de lectura sobre `sale.commission.rule`, el motor de seguridad de Odoo arroja un `AccessError`.

2. **Asignación errónea de porcentaje por defecto (`models/sale_order_line.py`):**  
   En la línea 34, el código retornaba:
   ```python
   return self.env.user.commission_percent
   ```
   Se utilizó `self.env.user` (usuario de la sesión activa que hace clic en el botón) en vez de `self.order_id.user_id.commission_percent` (el vendedor titular asignado a la orden).

### 3. Corrección Mínima Aplicada
Siguiendo el principio de cambio mínimo en caliente (*hotfix*) sin romper otras dependencias:
1. **Acceso de solo lectura en `security/ir.model.access.csv`:**  
   Se agregó una línea para que el grupo `sales_team.group_sale_salesman` tenga permiso exclusivamente de **lectura** (`perm_read=1, perm_write=0, perm_create=0, perm_unlink=0`):
   ```csv
   access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
   ```
   *No se concedieron permisos excesivos ni se recurrió al uso injustificado de `sudo()`.*

2. **Corrección de referencia de vendedor en `models/sale_order_line.py`:**  
   Se cambió la línea 34 para que referencie al vendedor del pedido:
   ```python
   return self.order_id.user_id.commission_percent
   ```

### 4. Prueba Automatizada
Se actualizaron y ampliaron las pruebas en `tests/test_sale_commission.py`:
- `test_commission_on_confirm`: Ahora ejecuta explícitamente `order.with_user(self.salesman).action_confirm()`, validando que un vendedor puede confirmar sus ventas.
- `test_manager_confirm_uses_salesman_commission`: Valida que cuando el gerente confirma un pedido en nombre de un vendedor, el porcentaje asignado a las líneas sea el del vendedor (`order.user_id.commission_percent`) y no el del gerente.

---

## Tramo B — Contención, Análisis y Comunicación

### 1. Plan de Contención en los Primeros 15 Minutos (Antes del Despliegue del Hotfix)
Si el incidente requiriera una acción inmediata en caliente antes de finalizar las pruebas del hotfix para garantizar la apertura a las 8:00 a.m.:
- **Opción A (Recomendada y Reversible):** Crear manualmente desde la interfaz de Odoo (o vía XML-RPC con usuario administrador) la regla de acceso de lectura temporal para `sale.commission.rule` asignada al grupo `Ventas / Usuario: solo sus documentos` (`sales_team.group_sale_salesman`).
  - *Riesgo:* Mínimo y nulo impacto en datos. Totalmente reversible al desplegar el módulo.
- **Opción B (No recomendada):** Asignar temporalmente a todos los vendedores el rol de Gerente de Ventas (`group_sale_manager`).
  - *Riesgo:* **Muy alto.** Otorga acceso a configuraciones comerciales, modificación de reglas de comisiones de otros compañeros y reportes de toda la empresa. Violación grave de seguridad y segregación de funciones.

### 2. Identificación del Commit y Falla en la Revisión
- **Commit causante:** `3f4d73fb2810f1fd650ce1de24557cb9b49624b3`  
  - *Mensaje:* `[FEAT] sale_commission: porcentaje de comisión por categoría de producto`  
  - *Fecha/Hora:* Desplegado el viernes al mediodía.
- **Por qué pasó la revisión:**
  1. En los tests unitarios del PR se alteró el método `_create_order` eliminando `.with_user(user)`.
  2. En el test se agregó `cls.env.user.commission_percent = 5.0` y se ejecutó la confirmación con el usuario administrador.
  3. El revisor de código asumió que la prueba en verde garantizaba el funcionamiento, sin verificar si la ejecución de la prueba corría con el contexto de seguridad restringido del vendedor.

### 3. Pasos para Desplegar y Verificar en Producción
1. Descargar la rama `hotfix/T-200` en el servidor de producción.
2. Actualizar el módulo con el CLI de Odoo:
   ```bash
   ./odoo-bin -c /etc/odoo/odoo.conf -d produccion -u sale_commission --stop-after-init
   ```
3. Reiniciar el servicio de Odoo (`systemctl restart odoo`).
4. **Verificación en producción:**
   - Iniciar sesión con un usuario vendedor real de pruebas.
   - Crear un pedido de venta borrador con 1 producto.
   - Confirmar el pedido y verificar que pase a estado "Pedido de Venta" sin error.
   - Verificar en la pestaña de líneas que el porcentaje y monto de comisión coincidan con la regla configurada.

### 4. Mensaje al Cliente (Comercial Los Andes C.A.)
> **Estimado equipo de Comercial Los Andes:**  
> Lamentamos profundamente los inconvenientes presentados esta tarde con la confirmación de pedidos. Hemos identificado y corregido la causa que impedía a los vendedores procesar sus ventas, y el sistema ya se encuentra 100% operativo y verificado para la jornada de mañana sábado a las 8:00 a.m. Adicionalmente, estamos revisando los pedidos confirmados durante la tarde para asegurar que todas las comisiones queden perfectamente registradas para cada vendedor.  
> *Equipo de Soporte y Desarrollo.*

---

## Tramo C — Impacto en Datos, Remediación y Prevención

### 1. Análisis del Impacto en los Datos
Durante la tarde, el gerente confirmó pedidos en nombre de los vendedores. Dado que la línea 34 leía `self.env.user.commission_percent`, todas las líneas de pedidos confirmados por el gerente cuyos productos no tenían una regla específica por categoría se grabaron con la comisión del **gerente** (usualmente 0% o un valor administrativo) en vez de la del **vendedor real del pedido**.

### 2. Script de Auditoría (Solo Lectura)
Se diseñó el script ejecutable [`scripts/audit_affected_commissions.py`](file:///c:/Users/PC/Desktop/pruebaBinaural/src/custom/prueba-tecnica/sale_commission/scripts/audit_affected_commissions.py), el cual:
- Recorre todos los pedidos confirmados hoy.
- Evalúa el porcentaje que le correspondía al vendedor (`order.user_id.commission_percent`) vs el porcentaje grabado en la línea.
- Imprime el detalle de cada pedido y línea afectada, cuantificando la diferencia en monto de comisión sin alterar la base de datos.

### 3. Plan de Remediación
Para corregir los pedidos afectados detectados por la auditoría:
1. Coordinar con el Gerente de Administración para ejecutar la corrección en horario de bajo tráfico.
2. Aprovechar el método nativo que Odoo ya posee en el módulo: [`action_recompute_commissions()`](file:///c:/Users/PC/Desktop/pruebaBinaural/src/custom/prueba-tecnica/sale_commission/models/sale_order.py#L13-L20). Este método ya calcula correctamente basándose en `order.user_id.commission_percent`:
   ```python
   line.commission_percent = rule[:1].percent if rule else order.user_id.commission_percent
   ```
3. Ejecutar el recálculo masivo desde el shell de Odoo para los pedidos identificados:
   ```python
   affected_order_ids = [...] # IDs reportados por audit_affected_commissions.py
   orders = env["sale.order"].browse(affected_order_ids)
   orders.action_recompute_commissions()
   env.cr.commit()
   ```
4. Re-ejecutar el script `audit_affected_commissions.py` para validar que el reporte devuelva 0 líneas con discrepancias.

### 4. Revisión de Otros Patrones Similares en el Módulo
Se auditó todo el módulo `sale_commission` buscando usos de `self.env.user`:
- Se confirmó que no existen otros modelos o métodos utilizando `self.env.user` en lógica transaccional de ventas.

### 5. Propuesta de Prevención Institucional
Para evitar que un error de permisos o de usuario activo vuelva a llegar a producción:
1. **Regla de CI/CD para Tests:**  
   Todo test que evalúe flujos operativos de usuarios finales (`action_confirm`, `create`, `write`) debe ejecutarse obligatoriamente con `.with_user(salesman)`. Se prohíbe el uso de `self.env` (administrador) en aserciones de flujos comerciales.
2. **Linter / Regla estática:**  
   Prohibir el acceso a `self.env.user` dentro de modelos que contengan un campo relacional `user_id` (como `sale.order`, `account.move`), exigiendo en su lugar `record.user_id`.
3. **Checklist de Code Review:**  
   Todo nuevo modelo expuesto debe acompañarse obligatoriamente de sus reglas en `ir.model.access.csv` validadas para los grupos operativos del módulo antes de otorgar el *Merge Approval*.

