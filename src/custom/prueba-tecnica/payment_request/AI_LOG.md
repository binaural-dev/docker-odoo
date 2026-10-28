# AI_LOG — payment_request (Ejercicio 4)

## Herramientas
- Claude Code (app de escritorio), modelo Claude Opus 5.5.

## Prompts clave
1. «Arranca el ejercicio 4-A (payment_request) en una rama nueva.»
   - Diseñó el modelo con las reglas en `write()` (campos bloqueados, transiciones y grupo por estado
     destino) para que valgan también ante un `write` por RPC, no solo desde el botón. Agregó una regla que no
     estaba en el pedido: nadie aprueba su propia solicitud. Quedó documentada como supuesto.
2. Pruebas de «lo que no se debe poder hacer»: aprobar por método y por `write`, editar una enviada, montos
   inválidos, transiciones inválidas y botones por grupo (inspeccionando la vista que recibe cada usuario).
3. «Sigue con el 4-B: niveles, actividad, wizards de rechazo y pago, account.payment y reporte PDF.»
   - Antes de programar, revisó en Odoo 18 los campos de `account.payment` (`memo` en lugar de `ref`),
     cuándo se genera el asiento y qué grupo hace falta para crear pagos. Agregó a la prueba del pago la
     verificación del asiento contra la cuenta por pagar, porque «registrado en contabilidad» no se cumplía
     solo con crear el pago.

4. «Sigue con el 4-C: USD pagado en VES, multicompañía, concurrencia y ARCHITECTURE.md.»
   - Propuso `SELECT ... FOR UPDATE NOWAIT` al inicio de cada transición y probarlo con dos conexiones reales
     a la base, porque con un solo cursor de prueba no hay concurrencia real. En ARCHITECTURE.md explicó por
     qué el aislamiento `REPEATABLE READ` de Odoo no alcanza solo (protege al final, después de crear el
     segundo pago).
   - Advirtió que `_convert` usa la última tasa disponible, o 1 si no hay ninguna. Por eso se exige una tasa
     cargada para el día del pago: si no, una solicitud de 100 USD se podría pagar como 100 Bs.

## Lo que la IA hizo mal
- **Referencia circular de grupos:** el primer borrador hacía que *Solicitante* implicara `base.group_user`
  y, a la vez, que `base.group_user` implicara *Solicitante*. Odoo rechaza esa recursión. Se corrigió antes
  de instalar, al releer el XML.
- **Una línea sin sentido en una prueba** (`fields.Date.today().year[:0]`, que falla con un entero). Se vio al
  revisar el archivo antes de correrlo.
- **Prueba del chatter mal planteada, dos veces:** primero asumió que el seguimiento se publica con
  `flush_all()` (se publica en el *precommit*), y luego leyó `mail.tracking.value` con el empleado, que no
  tiene permiso de lectura. Se detectó al correr las pruebas.

- **Hueco de seguridad en el primer borrador del tramo B:** las reglas estaban repartidas en `write()` y
  permitían `write({"state": "submitted", "approver_id": <cualquiera>})`, con lo que el solicitante elegía
  su propio aprobador. Del mismo modo, `write({"state": "paid"})` marcaba como pagada sin crear el pago. Se
  detectó al releer el código antes de probarlo. Se cambió a una regla única: los campos del flujo no se
  escriben nunca directamente, solo a través de los métodos, que validan y luego escriben con un `sudo()`
  acotado. Ahora hay una prueba con cuatro `write` directos de distintos roles.
- En el README del tramo B afirmó que «un administrador puede rechazar» una solicitud cuyo aprobador no está
  disponible, lo que contradice la regla que acababa de implementar (solo el aprobador asignado). Se corrigió
  al releer el README.

- **Tramo C:** el primer intento de bloqueo dejaba un `ERROR odoo.sql_db: bad query ... FOR UPDATE NOWAIT`
  en el registro cada vez que dos personas coincidían. Las pruebas pasaban, pero en producción habría
  parecido un error del servidor. Se detectó leyendo el registro de las pruebas y se silenció con
  `mute_logger`, como hace Odoo en su propio código.

## Lo que escribiste tú sin IA
- Todo el código, las pruebas y la documentación de este módulo los generó la IA (Claude Code); no escribí código a mano.
- El proceso de decisión técnico y de arquitectura estuvo de mi lado: la IA proponía enfoques y alternativas, y yo decidía cuál seguir, el alcance y el orden de trabajo, y aprobaba cada tramo antes de pasar al siguiente.
- Validé el resultado manualmente en Odoo: recorrí el flujo completo como empleado y como aprobador/tesorería (envío, rechazo con motivo, pago, pago en bolívares con tasa y reporte PDF).
