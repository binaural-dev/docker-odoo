# Solicitudes de pago con aprobación (`payment_request`)

Módulo para la gestión y control de solicitudes de pago a proveedores con flujo de aprobación jerárquico y registro en contabilidad/tesorería.

---

## Supuestos y Preguntas al Cliente

Como consultor funcional y técnico, tras analizar el requerimiento enviado por **Carolina Méndez (Gerente de Administración de Distribuidora Andina C.A.)**, se identificaron ambigüedades naturales del negocio. Se definieron supuestos para poder avanzar sin bloquear el desarrollo y las preguntas clave a formular en la siguiente reunión:

### Preguntas clave para Carolina:
1. **Facturas vs. Anticipos:** ¿Las solicitudes de pago deben asociarse obligatoriamente a una Factura de Proveedor (`account.move`) ya cargada en Odoo, o aplican también para anticipos y pagos sin factura previa?
2. **Umbral de Pagos Grandes:** ¿Cuál es el monto exacto a partir del cual una solicitud se considera "grande" y escala a la Gerencia? ¿Este umbral varía según el área o proveedor?
3. **Flujo de Aprobación:** ¿Un pago grande requiere aprobación escalonada (primero el Jefe de Área y posteriormente la Gerencia), o pasa directamente a la Gerencia?
4. **Cuentas y Diarios Contables:** ¿Desde qué diarios bancarios opera habitualmente Tesorería para los desembolsos en Bolívares y en Dólares?
5. **Retenciones Fiscales:** ¿Al momento de emitir el pago se deben calcular y retener montos por concepto de IVA o ISLR (comprobantes de retención)?

### Supuestos asumidos para avanzar en el desarrollo:
1. **Niveles configurables:** El concepto de "pagos grandes" no se fijó de forma rígida (*hardcoded*). Se diseñó un modelo flexible de niveles de aprobación (`payment.approval.level`) con montos mínimos dinámicos por compañía.
2. **Generación de Pagos:** Al pagar la solicitud, Tesorería genera un registro oficial `account.payment` (pago a proveedor saliente) vinculado al diario financiero seleccionado y a la tasa de cambio vigente.
3. **Conversión de Moneda:** Si la solicitud se generó en USD y el pago se efectúa desde un diario bancario en VES (Bolívares), se aplica la tasa de cambio oficial de Odoo (`res.currency.rate`) correspondiente a la fecha de pago.
4. **Inmutabilidad estricta:** Una vez enviada la solicitud (`state == 'sent'`), los campos críticos (proveedor, monto, concepto, fecha y moneda) quedan bloqueados en modo solo lectura en la interfaz de usuario (`readonly="state != 'draft'"`).

---

## Tramos completados
- **Tramo A:** Modelo `payment.request`, secuencia `SP/2026/0001`, máquina de estados (`draft`, `sent`, `approved`, `paid`, `rejected`), roles de seguridad (`Solicitante`, `Aprobador`, `Tesorería`), aislamiento de registros (`ir.rule`), inmutabilidad tras envío, validaciones de monto positivo y suite completa de pruebas unitarias.
- **Tramo B:**
  - **Niveles de aprobación configurables (`payment.approval.level`):** Gestión por monto mínimo, secuencia y usuario aprobador asignado por compañía.
  - **Asignación automática y actividades:** Al enviar la solicitud, el sistema determina el nivel de aprobación correspondiente al monto, asigna al aprobador y crea una actividad en el chatter (`mail.activity`).
  - **Control estricto de aprobación:** Solo el aprobador específicamente asignado puede aprobar o rechazar la solicitud. Al aprobarse, se registra auditoría de quién aprobó y en qué fecha/hora.
  - **Wizard de rechazo:** Permite ingresar un motivo obligatorio, el cual queda registrado en la solicitud y publicado en el chatter para retroalimentación al solicitante.
  - **Wizard de pago y vinculación contable:** Permite a Tesorería seleccionar el diario financiero de egreso y fecha, generando y validando el registro `account.payment` vinculado a la solicitud con un botón inteligente (*Smart Button*).
  - **Control anti doble-pago:** Validación estricta que impide generar múltiples pagos para una misma solicitud.
  - **Reporte impreso PDF (QWeb):** Documento formal con datos de la solicitud, desglose de montos, comprobante contable y cuadro de auditoría de aprobación (quién aprobó y cuándo).

---

## Cómo probar el módulo

```bash
# Ejecución con el runner de pruebas:
.\run_test.ps1 -Modules payment_request -Database prueba_limpia
```
O con el CLI de Odoo:
```bash
./odoo test -d prueba_limpia -m payment_request
```

