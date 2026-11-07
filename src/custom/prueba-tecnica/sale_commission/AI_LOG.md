# AI Log — `sale_commission` (Ticket T-200)

Registro del uso de herramientas de Inteligencia Artificial durante la investigación, diagnóstico y resolución del incidente crítico T-200.

---

## Incidente T-200: Error en Confirmación de Pedidos por Vendedores

### Herramienta utilizada
- Antigravity / LLM Asistente de Desarrollo Odoo.

### Prompts y consultas principales
- Análisis del ticket urgente enviado por el cliente (*Comercial Los Andes C.A.*).
- Inspección de los commits recientes (`git log`) para identificar el origen del cambio del mediodía (`3f4d73f`).
- Análisis de permisos en `ir.model.access.csv` y seguimiento del flujo de llamada de `action_confirm` hacia `_get_commission_percent()`.
- Detección de corrupción silenciosa de datos al analizar la llamada a `self.env.user.commission_percent`.
- Generación del script de auditoría de solo lectura en Python para detectar pedidos afectados.
- Redacción del reporte de incidente formal `INCIDENT.md`.

### Correcciones y decisiones del desarrollador humano
- **Principio de cambio mínimo en producción:** Se descartó reescribir la lógica de comisiones o reestructurar el modelo. La corrección se limitó a:
  1. Conceder permiso de solo lectura (`perm_read=1`) en `sale.commission.rule` al grupo `sales_team.group_sale_salesman` en `ir.model.access.csv`.
  2. Sustituir `self.env.user.commission_percent` por `self.order_id.user_id.commission_percent` en `sale_order_line.py`.
- **Rechazo de `sudo()`:** Se descartó elevar permisos mediante `sudo()` en `_get_commission_percent()`, ya que la política de comisiones por categoría es un dato maestro que los vendedores deben poder consultar legítimamente en modo solo lectura.
- **Validación con usuario no privilegiado:** Se corrigieron los tests unitarios para que la confirmación se ejecute estrictamente con el contexto del vendedor (`with_user(salesman)`), eliminando el falso positivo generado en la versión anterior.

### Validación y pruebas
- Reproducción del fallo antes de la corrección (`AccessError` y `AssertionError` en test unitario).
- Ejecución de la suite completa tras la corrección: 30/30 pruebas pasando en verde (7 de `sale_commission`, 17 de `payment_request` y 14 de `fleet_inspection`).
- Prueba exitosa del script de auditoría `scripts/audit_affected_commissions.py` detectando correctamente las líneas discrepantes.

