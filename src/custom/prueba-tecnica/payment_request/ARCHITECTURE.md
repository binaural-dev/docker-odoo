# ARCHITECTURE — `payment_request`

Decisiones de diseño del tramo C (y las del flujo en las que se apoyan). Para el uso, ver [README.md](README.md).

## 1. El flujo no se puede saltar

`write()` rechaza a **cualquier** usuario que intente cambiar el estado o los datos del flujo (aprobador,
aprobación, motivo, pago, tasa). Solo cambian a través de los métodos (`action_submit`, `action_approve`,
`action_reject`, `_create_payment`). Todos pasan por `_check_state_change()`, que en este orden:

1. Verifica acceso de escritura al registro (reglas de registro, que incluyen la compañía).
2. **Bloquea la fila en la base** (punto 2).
3. Valida la transición, el grupo del estado destino y, para aprobar o rechazar, que el usuario sea el
   aprobador asignado y no el solicitante.

Recién entonces el método escribe con un `sudo()` acotado (`_set_state`), que conserva el usuario para el
chatter. Así un `write` por RPC no puede elegir aprobador, aprobar ni marcar como pagada.

## 2. Concurrencia: bloqueo en la base, no un chequeo en Python

**Problema.** Si el aprobador aprueba y rechaza a la vez (dos pestañas), o dos personas de tesorería pagan la
misma solicitud, las dos transacciones leen «enviada» (o «aprobada») antes de que cualquiera escriba. Un
`if request.state == ...` en Python da `True` en ambas: dos decisiones, o **dos pagos**.

**Solución.** `_lock_for_update()` ejecuta `SELECT id FROM payment_request WHERE id IN (...) FOR UPDATE NOWAIT`
al comienzo de cada transición, y relee los campos después de bloquear.
- La primera transacción toma el bloqueo de la fila hasta su `COMMIT` o `ROLLBACK`.
- La segunda **no espera**: `NOWAIT` falla de inmediato (`LockNotAvailable`) y el usuario recibe «Otra
  persona está procesando esta solicitud…». No hace nada: ni crea el pago ni cambia el estado.
- Si la segunda llega después de que la primera terminó, toma el bloqueo, relee y ve el estado nuevo. La
  transición ya no es válida (por ejemplo, de «aprobada» a «rechazada»), así que falla con un mensaje claro.

**Por qué `FOR UPDATE NOWAIT`, y no confiar solo en el aislamiento de Odoo.** Odoo trabaja en `REPEATABLE
READ`: si dos transacciones escriben la misma fila, la segunda queda esperando y luego falla con un error de
serialización, que Odoo reintenta. Eso evita el doble estado, pero solo **al final**:
- el segundo pago ya se habría creado (y luego se deshace);
- el usuario espera bloqueado sin saber por qué;
- la protección depende del orden de las escrituras.

El bloqueo explícito actúa **antes** de cualquier efecto, responde enseguida y no depende de cómo esté escrito
el resto del método. El mensaje de `odoo.sql_db` por el intento fallido se silencia (`mute_logger`), igual
que hace Odoo en su propio código, porque es un caso esperado y no un error.

**Prueba.** `TestPaymentRequestConcurrency` abre **dos conexiones reales** a la base: aprobar y rechazar a la
vez, y dos tesoreros pagando a la vez. Verifica que la segunda falla mientras la primera tiene el bloqueo,
que sigue fallando después del `COMMIT` (por el estado nuevo) y que al final hay un solo pago. Una prueba con
un solo cursor no habría probado nada.

## 3. Pago todo o nada

`_create_payment()` crea y publica el `account.payment` **dentro de un savepoint** y solo después deja la
solicitud en «pagada». Si la creación o la publicación fallan (diario mal configurado, falta de tasa, error de
contabilidad), el savepoint deshace el pago a medio crear y se muestra «No se pudo registrar el pago…; la
solicitud sigue aprobada». Prueba: `test_failed_payment_leaves_request_approved`, que simula un fallo de
`action_post`.

## 4. Pago en otra moneda (USD → VES)

- La solicitud se registra en la moneda de la factura (por ejemplo USD). El **diario elegido define la moneda
  del pago** (por ejemplo «Banco en bolívares», en VES).
- Monto = `_convert` a la **tasa de la fecha del pago** (no la de la solicitud ni la de la aprobación). Se
  guarda la tasa aplicada (`payment_rate`) y se muestra en la solicitud, el chatter y el PDF.
- **Se exige una tasa cargada para ese día.** Sin ella, Odoo usaría la última tasa disponible (o 1 si no hay
  ninguna) y se pagaría un monto equivocado. Es mejor detener el pago con un mensaje que pagar mal.
- El asiento lo arma Odoo: la cuenta por pagar queda con 3.650 Bs (`amount_currency`) que valen 100 USD en la
  moneda de la compañía.
- El wizard muestra **antes de confirmar** la moneda, la tasa y el monto a pagar, con la misma función que el
  pago real.

## 5. Multicompañía

- `company_id` obligatorio en solicitudes y niveles, con **reglas de registro globales**
  (`company_id in company_ids`): aplican a todos los grupos, también a aprobadores y tesorería. Un usuario de
  la compañía B no ve ni lee nada de la A (prueba con lectura directa, no solo búsqueda).
- El nivel se busca **en la compañía de la solicitud**, y el aprobador de un nivel debe tener acceso a esa
  compañía (restricción). El diario del pago debe ser de la misma compañía.

## Límites conocidos

- La tasa se toma tal como está cargada en Odoo. Traer la tasa del BCV automáticamente es otro proyecto: se
  puede hacer con el servicio de tasas de Odoo o con un módulo de localización venezolana.
- `NOWAIT` responde «otra persona está procesando» aunque la otra transacción esté a punto de terminar. Es un
  falso negativo aceptable: el usuario recarga y ve el resultado.
