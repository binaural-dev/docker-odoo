# Stock: Quality Check on Transfers

## Goal
Implementar una verificación de calidad opcional al validar albaranes. Al transferir, debe aparecer un asistente para registrar si la mercancía aprueba o falla.

## Acceptance Tests
- Si la verificación está activada, el picking no puede completarse sin registrar el resultado.
- El asistente debe permitir indicar aprobación o rechazo.
- Incluir pruebas que aseguren que la transferencia se bloquea hasta completar la verificación.

## Evaluación
El código debe incluir pruebas automáticas y respetar las buenas prácticas de Odoo.
