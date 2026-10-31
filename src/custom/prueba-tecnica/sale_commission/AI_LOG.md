# AI_LOG — sale_commission

## Herramientas
- Antigravity (Google DeepMind / Gemini)

## Prompts clave (3 a 5)
1. "Analiza el historial de commits de sale_commission e identifica qué cambio causó que los vendedores no puedan confirmar pedidos."
   - Respuesta: Me señaló el commit `3f4d73f` que introdujo el modelo `sale.commission.rule` y modificó `sale_order_line.py`, evidenciando la falta de permisos de lectura para vendedores en `ir.model.access.csv`.
2. "¿Cómo estructurar una prueba unitaria en Odoo con TransactionCase para simular que un vendedor confirma un pedido y validar el AccessError?"
   - Respuesta: Me propuso usar `order.with_user(self.salesman).action_confirm()`. La incorporé en `test_sale_commission.py` para demostrar el fallo antes del fix.
3. "¿Por qué la confirmación del gerente en nombre de los vendedores afectó los porcentajes de comisión de los pedidos?"
   - Respuesta: Explicó que `sale_order_line.py` retornaba `self.env.user.commission_percent` en lugar de `self.order_id.user_id.commission_percent`. Con eso formulé el script de auditoría y la corrección del cálculo.

## Lo que la IA hizo mal
- En un primer análisis sugirió envolver la búsqueda de reglas con `.sudo()` en `sale_order_line.py`.
  - *Cómo me di cuenta:* Las instrucciones de la prueba técnica y las buenas prácticas de seguridad de Odoo desaconsejan el uso indiscriminado de `sudo()` cuando el problema es simplemente una regla de control de acceso faltante. Lo descarté y agregué el permiso de lectura en `ir.model.access.csv`.
- Sugirió dar permisos de escritura y creación al vendedor sobre `sale.commission.rule`.
  - *Cómo me di cuenta:* Violaría el principio de privilegio mínimo, ya que un vendedor no debe tener facultad para alterar las tablas de comisiones del negocio.

## Lo que escribiste tú sin IA
- El diagnóstico de que en el test original el autor había forzado `cls.env.user.commission_percent = 5.0` para ocultar el defecto en CI.
- La redacción del mensaje para el cliente en `INCIDENT.md`, adaptando el tono a un lenguaje corporativo y empático libre de jerga técnica.
- La definición de los pasos del plan de contención de 15 minutos en producción a través de la interfaz web de Odoo.
