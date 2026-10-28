# Solicitudes de pago (`payment_request`)

Solicitudes de pago a proveedores con aprobación (Ejercicio 4 de la prueba técnica). Odoo 18.

## Qué hace

- Cualquier empleado (todo usuario interno) crea una solicitud con **proveedor, monto, moneda y concepto**.
  El número se asigna solo: `SP/2026/0001`.
- Estados: **borrador → enviada → aprobada → pagada**, o **rechazada**. Cada cambio de estado queda en el
  chatter.
- Al **enviarla** ya no se puede modificar ni borrar: ni el solicitante ni el aprobador.
- **Aprobador** aprueba o rechaza; **Tesorería** registra el pago de las aprobadas.
- Menú *Solicitudes de pago*: *Solicitudes* (cada quien ve las suyas; aprobador y tesorería ven todas),
  *Por aprobar* (aprobador) y *Por pagar* (tesorería). Filtros por estado y agrupación por proveedor.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — modelo, estados, grupos, vistas, menú y pruebas | ✅ 16 pruebas, cobertura 98 %, sin advertencias al instalar |
| B — niveles de aprobación, wizards de rechazo y pago, `account.payment`, reporte PDF | ⏳ Pendiente |
| C — USD pagado en VES, multicompañía completa, concurrencia, ARCHITECTURE.md | ⏳ Pendiente (ya hay `company_id` y una regla de registro por compañía) |

## Cómo probarlo

```bash
./odoo test prueba-tecnica payment_request -d pr_prueba
```

A mano: crear un usuario solo con *Usuario interno* (queda como Solicitante), otro con *Solicitudes de pago ›
Aprobador* y otro con *Tesorería*, y recorrer el flujo con cada uno.

### Qué cubren las pruebas

Todas corren con usuarios de cada grupo (`with_user`), no como administrador.

| Requisito | Prueba |
|---|---|
| Secuencia `SP/AAAA/0001`, solicitante y moneda por defecto | `test_defaults_and_sequence` |
| Flujo completo hasta pagada, y rechazo | `test_full_flow_paid`, `test_reject_flow` |
| Cambios de estado en el chatter | `test_state_changes_are_tracked_in_chatter` |
| El solicitante solo ve sus solicitudes (ni buscarlas ni leerlas) | `test_requester_sees_only_own` |
| El solicitante **no aprueba**: ni por método… | `test_requester_cannot_approve_by_method` |
| …ni con un `write({"state": "approved"})` directo, como haría una llamada RPC | `test_requester_cannot_approve_by_write` |
| El solicitante no registra el pago | `test_requester_cannot_mark_paid` |
| Enviada = no se edita ni se borra (solicitante y aprobador) | `test_submitted_request_is_locked` |
| Monto cero o negativo, al crear y al modificar | `test_amount_must_be_positive` |
| Transiciones inválidas (aprobar sin enviar, pagar sin aprobar, aprobar una rechazada…) | `test_invalid_transitions` |
| Botones según estado y grupo (se inspecciona la vista que recibe cada usuario) | `test_buttons_by_group_and_state` |

## Decisiones de diseño

- **Las reglas viven en `write()`, no en los botones.** Esconder un botón no impide llamar al método por RPC,
  y llamar al método no impide hacer un `write` directo del estado. Por eso `write()` valida tres cosas:
  campos bloqueados después de enviar, que la transición de estado sea válida y que el usuario tenga el grupo
  del estado destino. Los botones solo se encargan de que el usuario no vea opciones que no puede usar.
- **Sin `sudo()`** en el módulo. El único `sudo()` está en una prueba, para leer el chatter y comprobar el
  resultado.
- **Nadie aprueba su propia solicitud**, aunque sea aprobador (separación de funciones).
- **Todo empleado es Solicitante:** `base.group_user` implica el grupo *Solicitante*, así que no hay que
  asignárselo a cada usuario. Los usuarios del portal quedan fuera.
- **¿Por qué no usar lo que Odoo ya trae?** La app *Aprobaciones* (con su tipo «Pago») es de Odoo Enterprise,
  y este entorno es Community. En Community, *Contabilidad* registra pagos a proveedores pero no tiene un
  flujo de solicitud y aprobación. El módulo **reutiliza** lo nativo donde existe: chatter y actividades
  (`mail`), proveedores (`res.partner`), monedas y, en el tramo B, `account.payment` para el pago.

## Supuestos y preguntas al cliente

Correo de Carolina Méndez (Distribuidora Andina C.A.). Para cada pregunta, lo que asumí para poder avanzar
sin su respuesta:

| # | Pregunta para Carolina | Supuesto mientras tanto |
|---|---|---|
| 1 | ¿A partir de qué monto un pago es «grande» y lo aprueba gerencia? ¿El monto se mide en bolívares o en dólares? | Tramo B: niveles configurables (monto mínimo → aprobador), comparados en la moneda de la compañía. En el tramo A, cualquier Aprobador aprueba |
| 2 | ¿Cómo se sabe quién es el «jefe del área» de cada empleado? ¿Usan la app de Empleados con departamentos y jefes? | No se depende de Empleados (no está en el pedido): el aprobador se configura en cada nivel |
| 3 | Un pago grande, ¿lo aprueba solo gerencia o primero el jefe del área y después gerencia? | Una sola aprobación, la del nivel que corresponde al monto |
| 4 | ¿Un aprobador puede aprobar sus propias solicitudes? | No. Separación de funciones |
| 5 | Si se rechaza, ¿el empleado corrige la misma solicitud y la vuelve a enviar, o crea una nueva? | Rechazada es un estado final; el empleado crea una nueva. Así queda el historial de lo rechazado |
| 6 | ¿El empleado puede anular una solicitud que ya envió? | No en el tramo A: se le pide al aprobador que la rechace |
| 7 | ¿Una solicitud se paga siempre completa, o puede haber pagos parciales? | Un solo pago por el monto completo |
| 8 | ¿El pago debe ir contra una factura del proveedor ya registrada (para conciliarla)? | Pago a proveedor independiente, vinculado a la solicitud. La conciliación con la factura la hace contabilidad como hoy |
| 9 | «Facturan en dólares y les pagamos en bolívares»: ¿la solicitud se hace en dólares? ¿Qué tasa se usa (BCV del día del pago, de la aprobación, otra)? | La solicitud se registra en la moneda de la factura. Tramo C: se paga desde un diario en VES a la tasa de la **fecha del pago** |
| 10 | ¿Hay que adjuntar la factura o un soporte para poder enviar? | Se puede adjuntar en el chatter, pero no es obligatorio |
| 11 | ¿Quiénes son «todos los empleados»: solo usuarios internos de Odoo? | Sí, todo usuario interno. Los usuarios del portal no |
| 12 | ¿Qué debe llevar la solicitud impresa para la carpeta del proveedor (firmas, sello, datos bancarios)? | Tramo B: número, proveedor, monto, concepto, solicitante y quién aprobó y cuándo |
| 13 | ¿Trabajan con más de una empresa en el mismo Odoo? | El modelo ya tiene compañía y una regla de registro por compañía. Niveles por compañía en el tramo C |
| 14 | ¿Al empleado le llega un correo cuando le aprueban o rechazan? | Lo sigue por el chatter: como creador es seguidor y recibe las notificaciones. En el tramo B el motivo de rechazo se publica ahí |

## Limitaciones conocidas

- Tramo A: «Registrar pago» solo cambia el estado; todavía no crea el pago en contabilidad (tramo B).
- El rechazo todavía no pide motivo (wizard del tramo B).
- No hay niveles de aprobación ni actividad para el aprobador (tramo B).
- Las vistas se validan al instalar y la visibilidad de los botones se prueba sobre la vista de cada usuario,
  pero las pantallas no se revisaron una por una en el navegador.
