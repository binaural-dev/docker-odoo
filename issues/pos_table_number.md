# Point of Sale: Table Number

## Goal
Permitir que el cajero asigne un número de mesa a cada pedido de punto de venta. Este número debe almacenarse en el modelo de orden y mostrarse en el recibo.

## Acceptance Tests
- Agregar el campo `table_number` en el modelo de órdenes de punto de venta.
- La interfaz debe permitir al usuario introducir el número de mesa.
- El recibo impreso debe incluir dicho número.
- Incluir una prueba que verifique que el campo se almacena y se muestra correctamente.

## Evaluación
El desarrollo debe seguir las guías de Odoo y contar con pruebas automatizadas.
