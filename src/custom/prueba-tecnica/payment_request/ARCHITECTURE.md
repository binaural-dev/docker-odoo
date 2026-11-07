# Arquitectura Técnica — `payment_request` (Tramo C)

Este documento detalla y justifica las decisiones arquitectónicas implementadas para responder a los requerimientos de multimoneda, aislamiento multi-compañía, concurrencia pesimista en base de datos y atomicidad transaccional.

---

## 1. Concurrencia y Control de Carrera (Database-Level Locking)

### Problema
En sistemas distribuidos y aplicaciones web como Odoo (manejadas mediante trabajadores/workers independientes), dos aprobadores o un aprobador y un tesorero pueden interactuar simultáneamente sobre la misma solicitud. Si el control se limita a validaciones en Python (`if self.state != 'sent'`), se genera una condición de carrera (*race condition*):
1. **Worker A** lee la fila: `state = 'sent'`.
2. **Worker B** lee concurrentemente la misma fila: `state = 'sent'`.
3. Ambos pasan la validación en memoria de Python.
4. Worker A aprueba la solicitud y Worker B la rechaza (o ambos aprueban); ambas transacciones intentan confirmar escrituras divergentes.

### Solución Implementada: `FOR UPDATE NOWAIT`
La concurrencia se resolvió a nivel de motor relacional (PostgreSQL) aplicando bloqueo exclusivo de fila:
```python
self.env.cr.execute(
    "SELECT id, state FROM payment_request WHERE id IN %s FOR UPDATE NOWAIT",
    [tuple(self.ids)],
)
self.invalidate_recordset(["state", "approver_id", "payment_id"])
```
- **Por qué en la base de datos y no en Python:** Python opera bajo aislamiento *Read Committed* por defecto en Odoo; la memoria local de un proceso worker no tiene visibilidad en tiempo real de transacciones concurrentes no confirmadas de otros procesos. PostgreSQL, en cambio, gestiona bloqueos a nivel de tupla (`RowExclusiveLock` / `XMAX`).
- **Por qué `NOWAIT`:** En lugar de dejar a la segunda transacción bloqueada esperando indefinidamente (lo que consumiría conexiones de pool y generaría *deadlocks* potenciales en la interfaz de usuario), `NOWAIT` arroja una excepción inmediata si otra transacción ya adquirió el cerrojo.
- **Resultado:** Solo el primer aprobador que interactúa gana el cerrojo y procesa la transición; el segundo aprobador recibe inmediatamente una notificación informándole que el registro está siendo procesado concurrentemente. Inmediatamente después del cerrojo, se ejecuta `invalidate_recordset()` para garantizar que cualquier lectura subsiguiente consulte los valores frescos de la base de datos.

---

## 2. Multimoneda: Pagos en VES de Solicitudes en USD

### Problema
Los proveedores emiten frecuentemente facturas en Dólares Americanos (USD), pero los desembolsos efectivos de tesorería se ejecutan desde cuentas bancarias nacionales en Bolívares (VES), requiriendo una tasa de cambio oficial aplicable a la fecha del pago.

### Solución Implementada
- En el asistente de pago (`payment.request.pay.wizard`), se identifican dinámicamente la moneda de la solicitud (`currency_id`) y la moneda operativa del diario bancario (`journal_currency_id`).
- Si las monedas difieren, se utiliza el motor nativo de tasas de Odoo:
  ```python
  payment_amount = currency_id._convert(
      amount, target_currency, company_id, payment_date
  )
  ```
- **Registro contable exacto:** El asiento `account.payment` se crea en la moneda del diario (VES) por el monto convertido a la tasa vigente a la `payment_date`.
- **Trazabilidad:** Se registra en el chatter de la solicitud el monto original en USD, la tasa de cambio empleada y el monto final desembolsado en VES, permitiendo auditorías transparentes.

---

## 3. Aislamiento Multi-Compañía

### Problema
En entornos multi-compañía, los usuarios pertenecientes a una compañía B no deben tener visibilidad ni acceso a las solicitudes de pago ni a las escalas de aprobación configuradas para la compañía A.

### Solución Implementada
- Modelos `payment.request` y `payment.approval.level` cuentan con el campo `company_id` obligatorio y valor por defecto de la compañía activa.
- Se implementaron reglas de registro globales (`ir.rule` con `global=True`):
  ```xml
  <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
  ```
- Al ser reglas globales, el ORM de Odoo las concatena con operador `AND` sobre cualquier otra regla de grupo o búsqueda, asegurando que ningún usuario de la Compañía B pueda ver, listar ni acceder por ID a registros de la Compañía A.
- La secuencia de numeración (`ir.sequence`) utiliza el prefijo con compañía activa (`with_company()`), garantizando numeración independiente por entidad jurídica.

---

## 4. Atomicidad Transaccional y Manejo de Fallas

### Problema
Si durante la generación o publicación del pago contable en Tesorería ocurre un error (cuenta contable desconfigurada, período fiscal cerrado, falta de saldo o excepción bancaria), la solicitud no debe quedar en estado `paid`.

### Solución Implementada
- **Orquestación estricta de operaciones:** En `action_confirm_payment()`, la creación del registro `account.payment` y su validación formal (`action_post()`) se ejecutan **antes** de mutar el estado de `payment.request`.
- **Rollback de PostgreSQL:** Al producirse cualquier excepción dentro del bloque transaccional de Odoo, el cursor de base de datos descarta todos los cambios de la transacción actual. La solicitud permanece inmutable en estado `approved` con `payment_id = False`, garantizando que nunca exista una solicitud marcada como pagada sin un comprobante contable válidamente emitido.

