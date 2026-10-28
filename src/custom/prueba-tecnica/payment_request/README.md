# Solicitudes de pago (`payment_request`)

Solicitudes de pago a proveedores con aprobación (Ejercicio 4 de la prueba técnica). Odoo 18.

## Qué hace

- Cualquier empleado (todo usuario interno) crea una solicitud con **proveedor, monto, moneda y concepto**.
  El número se asigna solo: `SP/2026/0001`.
- Estados: **borrador → enviada → aprobada → pagada**, o **rechazada**. Cada cambio de estado queda en el
  chatter.
- Al **enviarla** ya no se puede modificar ni borrar. Se le asigna el **aprobador del nivel** que corresponde
  al monto y se le crea una **actividad** («Aprobar solicitud de pago SP/…»).
- **Solo el aprobador asignado** aprueba o rechaza. Para rechazar hay que escribir un **motivo**, que queda en
  el chatter (con aviso al solicitante) y en la solicitud.
- **Tesorería** registra el pago con un wizard (diario y fecha). Se crea y publica el **pago a proveedor**
  (`account.payment`) con su asiento contable; queda vinculado a la solicitud (botón *Pago*) y la solicitud
  pasa a **pagada**. No se puede pagar dos veces.
- **Reporte PDF** (*Imprimir › Solicitud de pago*) para la carpeta del proveedor: datos de la solicitud,
  **quién aprobó y cuándo** (o el motivo del rechazo) y los datos del pago.
- Menú *Solicitudes de pago*: *Solicitudes*, *Por aprobar* (lo que le toca aprobar a cada aprobador),
  *Por pagar* (tesorería) y *Configuración › Niveles de aprobación* (administradores).

## Tramos completados

| Tramo | Estado |
|---|---|
| A — modelo, estados, grupos, vistas, menú y pruebas | ✅ |
| B — niveles de aprobación, actividad, wizards de rechazo y pago, `account.payment`, reporte PDF | ✅ 29 pruebas en total, cobertura 95 %, sin advertencias al instalar |
| C — USD pagado en VES, multicompañía completa, concurrencia, ARCHITECTURE.md | ⏳ Pendiente (ya hay `company_id` en solicitudes y niveles, y una regla de registro por compañía en las solicitudes) |

## Cómo probarlo

```bash
./odoo test prueba-tecnica payment_request -d pr_prueba
```

A mano:
1. *Configuración › Niveles de aprobación*: por ejemplo, desde 0 → jefe del área; desde 5.000 → gerente
   (ambos con el grupo *Solicitudes de pago › Aprobador*). Al instalar se crea un nivel desde 0 con el
   administrador.
2. Con un empleado (solo *Usuario interno*): crear y enviar una solicitud.
3. Con el aprobador asignado: verla en *Por aprobar*, aprobarla o rechazarla con motivo.
4. Con un usuario de *Tesorería*: *Por pagar › Registrar pago*, elegir el diario de banco.
5. *Imprimir › Solicitud de pago*.

### Qué cubren las pruebas

Todas corren con usuarios de cada grupo (`with_user`), no como administrador.

| Requisito | Prueba |
|---|---|
| Secuencia `SP/AAAA/0001`, solicitante y moneda por defecto | `test_defaults_and_sequence` |
| Flujo completo hasta pagada | `test_full_flow_paid` |
| Cambios de estado en el chatter | `test_state_changes_are_tracked_in_chatter` |
| El solicitante solo ve sus solicitudes (ni buscarlas ni leerlas) | `test_requester_sees_only_own` |
| El solicitante **no aprueba ni rechaza** llamando a los métodos | `test_requester_cannot_approve_by_method` |
| Nadie cambia estado, aprobador, aprobación ni pago con un `write` directo (RPC), ni siquiera aprobador o tesorería | `test_flow_fields_cannot_be_written_directly` |
| El solicitante no registra el pago (ni con el wizard ni con el método) | `test_requester_cannot_pay` |
| Una solicitud nueva no puede nacer en otro estado ni con aprobador | `test_requester_cannot_create_in_other_state` |
| Enviada = no se edita ni se borra (solicitante y aprobador) | `test_submitted_request_is_locked` |
| Monto cero o negativo, al crear y al modificar | `test_amount_must_be_positive` |
| Nadie aprueba su propia solicitud; no se envía si el nivel asignaría al propio solicitante | `test_approver_cannot_approve_own_request` |
| Transiciones inválidas (pagar sin aprobar, enviar dos veces, aprobar una rechazada…) | `test_invalid_transitions` |
| Botones según estado, grupo y aprobador asignado (se inspecciona la vista que recibe cada usuario) | `test_buttons_by_group_and_state` |
| **B** · El aprobador sale del nivel según el monto (bordes 4.999,99 y 5.000) | `test_level_assigned_by_amount` |
| **B** · El umbral se compara en la moneda de la compañía | `test_level_uses_company_currency` |
| **B** · Actividad para el aprobador asignado, que se cierra al aprobar | `test_activity_for_assigned_approver` |
| **B** · Sin nivel configurado no se puede enviar | `test_no_level_blocks_submit` |
| **B** · **Solo el aprobador asignado** aprueba o rechaza (otro aprobador no) | `test_only_assigned_approver_can_approve` |
| **B** · El aprobador de un nivel debe tener el grupo Aprobador; ni solicitante ni aprobador configuran niveles | `test_level_approver_must_be_approver`, `test_requester_cannot_configure_levels` |
| **B** · Wizard de rechazo: el motivo queda en el chatter y en la solicitud; la actividad se cierra | `test_reject_wizard_reason_in_chatter` |
| **B** · El motivo es obligatorio (vacío o solo espacios) | `test_reject_requires_reason` |
| **B** · Wizard de pago: pago a proveedor publicado, con asiento contra la cuenta por pagar, vinculado y visible desde la solicitud | `test_payment_wizard_creates_linked_vendor_payment` |
| **B** · **No se puede pagar dos veces** (wizard y método); queda un solo pago | `test_cannot_pay_twice` |
| **B** · El aprobador no paga | `test_approver_cannot_pay` |
| **B** · El PDF muestra quién aprobó y cuándo; si se rechazó, el motivo | `test_report_shows_who_approved_and_when`, `test_report_rejected_shows_reason` |

## Decisiones de diseño

- **El estado y los datos del flujo nunca se escriben directamente.** `write()` rechaza a cualquier usuario
  que intente cambiar `state`, `approver_id`, `approved_by_id`, `approval_date`, `rejection_reason` o
  `payment_id`. Esos campos solo cambian a través de los métodos del flujo (`action_submit`,
  `action_approve`, `action_reject`, `_create_payment`). Cada método primero valida
  (`_check_state_change`): acceso de escritura al registro, transición válida, grupo del estado destino y,
  para aprobar o rechazar, que el usuario sea el aprobador asignado y no el solicitante. Así, ni con un
  `write` por RPC se puede elegir el aprobador, aprobar o marcar como pagada sin crear el pago. Los botones
  solo esconden lo que el usuario no puede usar.
- **Dos `sudo()`, acotados y justificados en el código:**
  1. `_set_state()` escribe los campos del flujo **después** de las validaciones. `sudo()` conserva el
     usuario, así que el chatter registra a quien hizo el cambio.
  2. `_get_approval_level()` lee los niveles, para que el solicitante no necesite permiso sobre la
     configuración de aprobaciones.
- **Tesorería implica el grupo *Facturación* de Contabilidad**, porque registrar el pago crea un
  `account.payment`. No se usa `sudo()` para crear el pago: queda a nombre del usuario de tesorería.
- **Nivel = el de mayor monto mínimo que no supere el monto de la solicitud**, convertido a la moneda de la
  compañía a la fecha de la solicitud. Un nivel desde 0 cubre todo lo que está por debajo del siguiente.
- **Nadie aprueba su propia solicitud.** Si el nivel asignaría al propio solicitante, no se puede enviar y se
  pide configurar otro aprobador.
- **¿Por qué no usar lo que Odoo ya trae?** La app *Aprobaciones* (con su tipo «Pago») es de Odoo Enterprise,
  y este entorno es Community. El módulo **reutiliza** lo nativo donde existe: chatter y actividades,
  proveedores, monedas y tasas, y `account.payment` (con su asiento) para el pago.

## Supuestos y preguntas al cliente

Correo de Carolina Méndez (Distribuidora Andina C.A.). Para cada pregunta, lo que asumí para poder avanzar
sin su respuesta:

| # | Pregunta para Carolina | Supuesto mientras tanto |
|---|---|---|
| 1 | ¿A partir de qué monto un pago es «grande» y lo aprueba gerencia? ¿El monto se mide en bolívares o en dólares? | Niveles configurables (monto mínimo → aprobador), comparados en la moneda de la compañía a la fecha de la solicitud |
| 2 | ¿Cómo se sabe quién es el «jefe del área» de cada empleado? ¿Usan la app de Empleados con departamentos y jefes? | No se depende de Empleados (no está en el pedido): el aprobador se configura en cada nivel. Si cada área tiene su jefe, haría falta un nivel por departamento |
| 3 | Un pago grande, ¿lo aprueba solo gerencia o primero el jefe del área y después gerencia? | Una sola aprobación, la del nivel que corresponde al monto |
| 4 | ¿Un aprobador puede aprobar sus propias solicitudes? | No. Separación de funciones |
| 5 | Si se rechaza, ¿el empleado corrige la misma solicitud y la vuelve a enviar, o crea una nueva? | Rechazada es un estado final; el empleado crea una nueva. Así queda el historial de lo rechazado |
| 6 | ¿El empleado puede anular una solicitud que ya envió? | No: se le pide al aprobador que la rechace |
| 7 | ¿Una solicitud se paga siempre completa, o puede haber pagos parciales? | Un solo pago por el monto completo |
| 8 | ¿El pago debe ir contra una factura del proveedor ya registrada (para conciliarla)? | Pago a proveedor independiente, vinculado a la solicitud. La conciliación con la factura la hace contabilidad como hoy |
| 9 | «Facturan en dólares y les pagamos en bolívares»: ¿la solicitud se hace en dólares? ¿Qué tasa se usa (BCV del día del pago, de la aprobación, otra)? | La solicitud se registra en la moneda de la factura. Tramo C: se paga desde un diario en VES a la tasa de la **fecha del pago** |
| 10 | ¿Hay que adjuntar la factura o un soporte para poder enviar? | Se puede adjuntar en el chatter, pero no es obligatorio |
| 11 | ¿Quiénes son «todos los empleados»: solo usuarios internos de Odoo? | Sí, todo usuario interno. Los usuarios del portal no |
| 12 | ¿Qué debe llevar la solicitud impresa para la carpeta del proveedor (firmas, sello, datos bancarios)? | Número, estado, proveedor y RIF, monto, fecha, concepto, solicitante, aprobador asignado, quién aprobó y cuándo (o el motivo del rechazo) y los datos del pago |
| 13 | ¿Trabajan con más de una empresa en el mismo Odoo? | Solicitudes y niveles tienen compañía; regla de registro por compañía en las solicitudes. El resto en el tramo C |
| 14 | ¿Al empleado le llega un correo cuando le aprueban o rechazan? | Lo sigue por el chatter (como creador es seguidor). Al rechazar se le notifica con el motivo |
| 15 | ¿Quién define y mantiene los niveles de aprobación? | Los administradores de Odoo (*Ajustes*). Los aprobadores pueden verlos, no cambiarlos |

## Limitaciones conocidas

- Si cambia la configuración de niveles, las solicitudes ya enviadas conservan su aprobador asignado (no se
  reasignan).
- Si el aprobador asignado no está disponible (vacaciones), no hay delegación ni reasignación desde la
  interfaz: solo el aprobador asignado puede aprobar o rechazar, también frente a un administrador. Mejora
  propuesta: un botón «Reasignar aprobador» para administradores, que quede en el chatter.
- Pago en otra moneda distinta a la de la solicitud, multicompañía completa y concurrencia: tramo C.
- Las vistas se validan al instalar y la visibilidad de los botones se prueba sobre la vista de cada usuario,
  pero las pantallas no se revisaron una por una en el navegador.
