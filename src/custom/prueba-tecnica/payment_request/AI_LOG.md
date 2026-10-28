# AI_LOG — payment_request

## Herramientas
- Antigravity (Google DeepMind / Gemini)

## Prompts clave (3 a 5)
1. "¿Cómo declarar una regla de registro (ir.rule) en Odoo 17 para que los usuarios del grupo Solicitante solo puedan consultar y editar sus propias solicitudes de pago?"
   - Respuesta: Me proporcionó la definición XML con el dominio `[('user_id', '=', user.id)]` y vinculación al grupo `group_payment_request_user`. La integré en `security/payment_request_security.xml`.
2. "¿Cuál es la sintaxis en Odoo 17 para condicionar la visibilidad de botones según el estado y grupo sin usar los atributos obsoletos `attrs` ni `states`?"
   - Respuesta: Explicó el uso directo de `invisible="state != 'draft'"` y `groups="payment_request.group_..."`. Lo apliqué en la cabecera de la vista de formulario.
3. "¿Cómo impedir a nivel del ORM que un registro se edite una vez que cambia de estado, además de la restricción en la vista XML?"
   - Respuesta: Recomendó sobreescribir el método `write()` para interceptar cambios en campos sensibles cuando `state != 'draft'` y lanzar `UserError`. Lo implementé en `models/payment_request.py`.

## Lo que la IA hizo mal
- Intentó definir los botones de la cabecera del formulario usando `states="draft"` y `states="submitted"`.
  - *Cómo me di cuenta:* La documentación de Odoo 17 y las directrices de la prueba prohíben explícitamente `states` y `attrs` por ser sintaxis obsoleta de versiones anteriores. Lo corregí utilizando `invisible="state != 'condicion'"`.
- Sugirió dejar la validación de seguridad de aprobación únicamente en la vista XML (ocultando el botón al solicitante).
  - *Cómo me di cuenta:* Ocultar un botón en la vista es insuficiente porque un usuario técnico o llamada RPC puede invocar el método Python directamente. Añadí la validación en backend con `self.env.user.has_group()` dentro de `action_approve()`.

## Lo que escribiste tú sin IA
- El análisis funcional y formulación de preguntas de negocio para el cliente ficticio (Carolina Méndez) en el `README.md`.
- El diseño de la suite de pruebas unitarias que cubre deliberadamente escenarios de acceso denegado y reglas de registro entre múltiples usuarios.
