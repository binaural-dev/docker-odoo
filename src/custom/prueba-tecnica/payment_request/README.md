# Solicitudes de Pago a Proveedores (`payment_request`)

Módulo que permite a los empleados formalizar solicitudes de pago a proveedores con un flujo de estados y control de aprobaciones por jerarquía.

## Tramos Completados
- **Tramo A:** Modelo base `payment.request` con `mail.thread` y `mail.activity.mixin`, secuencia automática (`SP/%(year)s/0001`), estados de flujo (`draft` → `submitted` → `approved` → `paid` / `rejected`), grupos de seguridad (`Solicitante`, `Aprobador`, `Tesorería`), regla de registro para aislamiento de solicitantes, restricciones de validación (monto positivo e inmutabilidad post-envío), vistas Odoo 17 y pruebas unitarias completas.

---

## Supuestos y Preguntas al Cliente (Carolina Méndez — Distribuidora Andina C.A.)

Al analizar el requerimiento de Carolina como consultor funcional y técnico, identificamos vacíos operativos donde se tomaron supuestos arquitectónicos para no detener el desarrollo:

### 1. ¿Qué le preguntaríamos a Carolina?
1. **Umbral de Aprobación Jefatura vs. Gerencia:**  
   * *Pregunta:* "¿A partir de qué monto exacto una solicitud pasa de requerir aprobación de jefe de área a requerir aprobación de gerencia (ej. $1.000, $5.000)? ¿Este umbral varía según el departamento o tipo de gasto?"
2. **Registro Contable y Vinculación con Facturas:**  
   * *Pregunta:* "¿Las solicitudes de pago siempre corresponden a una factura de proveedor ya registrada en Odoo (`account.move`), o son adelantos/anticipos sin factura previa? ¿Desde qué diarios contables suele pagar Tesorería?"
3. **Manejo de Multimoneda y Tasa de Cambio (USD vs. VES):**  
   * *Pregunta:* "Mencionas que muchos proveedores facturan en dólares pero pagan en bolívares: ¿qué tasa oficial se utiliza para la conversión al momento del pago (tasa BCV del día, tasa de la factura o una pactada)? ¿Quién absorbe el diferencial cambiario?"
4. **Flujo de Rechazo y Corrección:**  
   * *Pregunta:* "Si una solicitud es rechazada, ¿el empleado debe corregirla sobre el mismo registro y reenviarla, o debe crear una solicitud completamente nueva para fines de auditoría?"

### 2. ¿Qué asumimos para avanzar en el Tramo A?
1. **Flujo Jerárquico Base:** Implementamos el rol general de *Aprobador* (`group_payment_request_approver`) que valida el paso de `submitted` a `approved`. En el Tramo B se incorporan los niveles configurables por monto (`payment.approval.level`).
2. **Inmutabilidad de la Solicitud:** Asumimos que los datos sustantivos (proveedor, monto, moneda, concepto y fecha) quedan estrictamente bloqueados contra edición una vez que la solicitud pasa a estado `submitted`, tanto en la interfaz gráfica (`readonly="state != 'draft'"`) como a nivel ORM en el método `write()`.
3. **Privacidad y Reglas de Registro:** Asumimos que los empleados comunes no deben ver las solicitudes ni los montos pedidos por otros compañeros de trabajo; por ende, se aplicó una regla de registro (`ir.rule`) que restringe al solicitante a ver solo sus propios registros (`user_id = user.id`), mientras que Aprobadores y Tesorería supervisan la totalidad de las solicitudes.
4. **Secuencia de Registro:** Se estableció la nomenclatura estandarizada `SP/YYYY/####` sugerida en el enunciado para fácil indexación en el archivo físico y carpetas de proveedores.

---

## Cómo Probarlo

### 1. Pruebas Automatizadas
Correr la suite de pruebas unitarias que valida el ciclo de vida, la seguridad y las restricciones:

```bash
./odoo test prueba-tecnica payment_request
```

O en la verificación general con base limpia:
```bash
./odoo test -d prueba_limpia -m payment_request
```

### 2. Verificación Manual en la Interfaz
1. Ingresar con un usuario perteneciente al grupo **Solicitante**:
   - Ir a **Solicitudes de Pago > Operaciones > Todas las Solicitudes**.
   - Crear una solicitud indicando proveedor, monto y concepto. Verificar que se genere la secuencia `SP/2026/0001`.
   - Presionar **"Enviar para Aprobación"**.
   - Verificar que los campos queden bloqueados en solo lectura y que el botón "Aprobar" no esté disponible.
2. Ingresar con un usuario del grupo **Aprobador**:
   - Verificar que pueda ver la solicitud enviada y presionar **"Aprobar"** o **"Rechazar"**.
3. Ingresar con un usuario de **Tesorería**:
   - Verificar que en estado *Aprobada* aparezca el botón **"Registrar Pago"** para formalizar el cierre del documento.

---

## Limitaciones Conocidas

- En el Tramo A, la generación del asiento contable de pago (`account.payment`) se modela mediante el estado `paid` y notas en el chatter; la generación automática del comprobante y conciliación contable se profundiza en el Tramo B mediante el wizard de pago.
