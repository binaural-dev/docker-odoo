# AI Log — `payment_request`

Registro del uso de herramientas de Inteligencia Artificial durante el análisis y desarrollo del módulo.

## Tramo A — Modelo Base, Seguridad y Flujo de Aprobación

### Herramienta utilizada
- Antigravity / LLM Asistente de Desarrollo Odoo.

### Prompts y consultas principales
- Análisis consultivo del correo de requerimientos de la clienta (Carolina Méndez).
- Identificación de ambigüedades funcionales para estructurar la sección de supuestos y preguntas al cliente.
- Diseño de la máquina de estados, vistas XML y reglas de seguridad (`ir.rule` para solicitantes).

### Correcciones y decisiones del desarrollador humano
- **Rechazo de sobreescritura de `write()`:** La IA propuso inicialmente interceptar `write()` en Python para validar la inmutabilidad de los campos enviados. El desarrollador rechazó esta propuesta por considerarla una mala práctica en Odoo, prefiriendo la vía declarativa estándar del framework: delegar el control de solo lectura a la vista XML (`readonly="state != 'draft'"`) y validarlo en tests mediante la clase `odoo.tests.common.Form`.
- **Regla estricta de auto-aprobación:** Se aseguró que ningún usuario pueda auto-aprobar solicitudes que él mismo haya emitido, validando el grupo `group_payment_request_approver` y la disparidad `applicant_id != env.user`.
- **Validación de montos:** Uso exclusivo del decorador estándar `@api.constrains("amount")` para montos mayores a cero.
- **Aislamiento de solicitudes:** Configuración precisa de `ir.rule` para que los solicitantes vean únicamente sus registros, mientras aprobadores y tesorería acceden a la totalidad.

### Validación y pruebas
- Pruebas automatizadas ejecutadas con `TransactionCase` y `Form`, verificando el ciclo de vida, montos inválidos, bloqueo de auto-aprobación, inmutabilidad de interfaz con `Form` y reglas de registro.
