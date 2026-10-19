# Comisiones de vendedores (`sale_commission`)

Calcula la comisión del vendedor en cada línea de pedido de venta y ofrece un análisis mensual por vendedor.

## Configuración

- **Porcentaje del vendedor:** Ajustes › Usuarios › pestaña *Comisiones* (solo gerentes de ventas).
- **Porcentaje por categoría (desde la 1.1):** Inventario/Ventas › Configuración › Categorías de producto,
  campo *Comisión (%)*. Si la categoría (o una categoría padre) tiene porcentaje, reemplaza al del vendedor.

## Cómo funciona

- Al confirmar el pedido se fija el porcentaje en cada línea y se calcula la comisión sobre el subtotal sin impuestos.
- El botón *Recalcular comisiones* del pedido vuelve a aplicar los porcentajes vigentes.
- Ventas › Reportes › *Comisiones*: tabla dinámica y gráfico por vendedor y mes. Cada vendedor ve solo lo suyo.

## Pruebas

```bash
./odoo test prueba-tecnica sale_commission
```
---

## Estado del Módulo
* **Ticket Resuelto:** `T-200` (Error de permisos que bloqueaba a los vendedores al confirmar pedidos).
* **Rama de trabajo:** `hotfix/T-200`
* **Documentación técnica:** Ver [INCIDENT.md](INCIDENT.md) para el reporte forense detallado del incidente, plan de contingencia, script de auditoría y análisis de causa raíz.

## Cómo Probar la Corrección
Para validar que la corrección permite a los vendedores confirmar pedidos de forma regular:
```bash
./odoo test prueba_v19 sale_commission