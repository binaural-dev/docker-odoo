# Comisiones de vendedores (`sale_commission`)

Calcula la comisión del vendedor en cada línea de pedido de venta y ofrece un análisis mensual por vendedor.

## Tramos Completados
- **Tramo A:** Reproducción y solución de la causa raíz del ticket T-200 (`AccessError` por permisos en `sale.commission.rule`). Corrección en `ir.model.access.csv` y pruebas unitarias con usuario vendedor.
- **Tramo B:** Diagnóstico del commit introductorio (`3f4d73f`), plan de contención de 15 minutos, pasos de despliegue y mensaje corporativo para el cliente. Documentado en `INCIDENT.md`.
- **Tramo C:** Corrección del error de asignación de comisiones (`self.env.user` reemplazado por `self.order_id.user_id`), script de auditoría de sólo lectura en Python para detectar pedidos afectados, plan de corrección de datos con `action_recompute_commissions()` y directrices preventivas de code review.

## Configuración

- **Porcentaje del vendedor:** Ajustes › Usuarios › pestaña *Comisiones* (solo gerentes de ventas).
- **Porcentaje por categoría (desde la 1.1):** Inventario/Ventas › Configuración › Categorías de producto,
  campo *Comisión (%)*. Si la categoría (o una categoría padre) tiene porcentaje, reemplaza al del vendedor.

## Cómo funciona

- Al confirmar el pedido se fija el porcentaje en cada línea y se calcula la comisión sobre el subtotal sin impuestos.
- El botón *Recalcular comisiones* del pedido vuelve a aplicar los porcentajes vigentes.
- Ventas › Reportes › *Comisiones*: tabla dinámica y gráfico por vendedor y mes. Cada vendedor ve solo lo suyo.

## Cómo probarlo

Ejecutar las pruebas unitarias que validan la confirmación por parte de vendedores y la preservación de porcentajes:

```bash
./odoo test prueba-tecnica sale_commission
```

O en la suite completa:
```bash
./odoo test -d prueba_limpia -m sale_commission
```

## Supuestos y Limitaciones Conocidas

- **Supuesto de seguridad:** El grupo `sales_team.group_sale_salesman` requiere únicamente permiso de lectura (`perm_read = 1`) en `sale.commission.rule`, garantizando que la configuración de porcentajes por categoría permanezca exclusiva para los gerentes de ventas.
- **Supuesto de asignación:** Si un pedido no tiene vendedor asignado (`user_id = False`), la comisión por defecto es 0.0 % si no aplica ninguna regla por categoría.
- **Limitación conocida:** La confirmación manual masiva desde vistas de lista requerirá que cada orden conserve individualmente el vendedor de su respectivo encabezado.
