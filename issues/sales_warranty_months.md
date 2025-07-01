# Sales: Warranty Months

## Goal
Añadir un campo `warranty_months` en los productos que indique la cantidad de meses de garantía. Este valor debe copiarse a las líneas de la orden de venta y mostrarse en el reporte de presupuesto.

## Acceptance Tests
- El campo `warranty_months` debe estar disponible en `product.template` y `product.product`.
- Al crear una orden de venta, el valor debe propagarse a las líneas de venta.
- El reporte de la orden de venta debe mostrar dicho valor.
- Incluir una prueba que verifique la propagación correcta del campo.

## Evaluación
El código debe seguir las convenciones de Odoo y contar con pruebas automáticas exitosas.
