---
name: odoo-currency-migration
description: Migra la moneda base de una compañía en Odoo (ej. USD -> Bs/VEF) sin perder el histórico contable, usando el campo "alterno" que ya calcula l10n_ve_accountant (odoo-venezuela) como fuente del nuevo valor. Usar cuando el usuario pida cambiar/migrar la moneda de la compañía de un cliente, "hacer lo mismo que con Proalca" para otro cliente, o continuar/ajustar una migración de moneda ya en curso (correcciones de residual, reconciliación, comparación contra la BD original, etc.). Nace del proyecto Proalca (2026-08) pero es multi-cliente: Proalca fue el primero de varios.
---

# Skill: odoo-currency-migration

Este skill vive fuera de cualquier proyecto de cliente a propósito -- la
memoria de Claude Code es específica por carpeta de trabajo, así que este es
el mecanismo para que el conocimiento viaje entre clientes.

**Fuente de verdad extendida:**
`/Users/binaural31/Documents/docker-odoo-17.0/scripts/currency-migration-playbook/METODOLOGIA.md`
-- léela al invocar este skill si hace falta el detalle completo, los
ejemplos reales, o el razonamiento largo detrás de cada regla. Este archivo
es el procedimiento accionable resumido; ese otro es el "por qué" con casos
reales (Proalca). **Este skill se sigue ajustando con cada cliente nuevo** --
si en una migración aparece un caso no cubierto aquí, edita este archivo Y
`METODOLOGIA.md` al cerrar la sesión (el primero es el checklist operativo,
el segundo es el archivo con el detalle/casos reales -- no dupliques
razonamiento largo aquí, referencia el otro).

Los scripts reusables (parametrizados por `.env`, sin ids hardcodeados) están
en `/Users/binaural31/Documents/docker-odoo-17.0/scripts/proalca-currency-migration/`
(`config.py`, `steps.py`, `run.py`, `lib/db.py`) -- para un cliente nuevo, se
copia esa carpeta completa como plantilla.

## 0. Detectar el modo

- **Cliente nuevo** (primera vez que se toca este cliente): ir a la sección 1.
- **Migración en curso** (ya hay `.env`/BD de prueba de este cliente): saltar
  a la sección 3, pero releer la bitácora del cliente primero para no repetir
  una decisión ya tomada ni una pregunta ya respondida.

## 1. Setup con un cliente nuevo

1. Copiar `scripts/proalca-currency-migration/` a una carpeta nueva con el
   nombre del cliente (ej. `scripts/<cliente>-currency-migration/`).
   Mantener `config.py`, `steps.py`, `run.py`, `lib/`. Borrar/vaciar los
   artefactos específicos de Proalca (`BITACORA_EJECUCION.md`,
   `LECCIONES.md`, CSVs de reporte) y arrancar una bitácora nueva para este
   cliente (mismo formato, contenido propio).
2. Completar `.env` a partir de `.env.example`: host/puerto/db/usuario de
   Postgres, `COMPANY_ID`, `OLD_COMPANY_CURRENCY_ID`/`NAME`,
   `NEW_COMPANY_CURRENCY_ID`/`NAME`, y revisar si los umbrales de detección
   (`MAX_PLAUSIBLE_RATE`, `RATE_MARGIN_MULTIPLIER`,
   `ZERO_IMPACT_ABS_THRESHOLD`) siguen teniendo sentido para el histórico de
   tasas de este cliente. **`ZERO_IMPACT_ABS_THRESHOLD` no es arbitrario
   aunque lo parezca** (ver METODOLOGIA.md y `feedback_odoo_orm_safety`
   regla 7 en la memoria de Proalca) -- si se baja o se quita, medir
   asientos desbalanceados antes/después, no confiar en el razonamiento
   lógico solo.
3. Confirmar que el cliente usa `l10n_ve_accountant` (o un módulo equivalente
   que guarde un campo "alterno" `foreign_debit`/`foreign_credit`/
   `foreign_balance`, `store=True`, calculado a la tasa histórica real) --
   si no, el pipeline entero necesita rediseño, no es un ajuste de `.env`.

## 2. Las preguntas obligatorias al cliente (antes de correr NADA)

Usar `AskUserQuestion`, no asumir la respuesta del cliente anterior. Estas
posturas son legítimas y cambian el resto del trabajo:

1. **¿Qué hacer con la corrupción histórica que reporte `detect()`?**
   (a) aproximar rápido (`repair()` con `debit * tasa histórica`), (b)
   reconstrucción exacta (motor real del módulo, solo lectura -- ver
   `reconstruct_exact.py` de Proalca como plantilla), o (c) no tocar nada.
2. **¿Le importa el detalle bruto débito/crédito por línea (turnover), o
   solo el balance neto?** Cambia qué tan lejos se puede llegar si aparece
   un choque con una restricción de Postgres (ver sección 5).
3. Al aparecer cualquier valor que se vea "raro" (total en 0, residual que
   no cuadra, ambos lados de una línea poblados): **preguntar si es
   corrupción o una práctica/cuadre deliberado del cliente antes de
   tocarlo.** No asumir.
4. **¿El alcance es solo contabilidad, o también cotizaciones/pedidos de
   venta (`sale.order`) y órdenes de compra (`purchase.order`)?** Proalca
   (2026-08-19) pidió extender a ambos con el mismo criterio que facturas
   (mostrar en Bs usando el "alterno" ya calculado). Si el cliente nuevo
   también lo pide, `steps.py` ya trae `fix_sale_order_currency()`/
   `fix_purchase_order_currency()` como plantilla (pasos 7/8, opcionales,
   fuera de `all`) -- copiarlos/adaptarlos en vez de reescribir desde cero,
   pero no asumir que la respuesta es la misma sin preguntar.

Documentar la respuesta en la bitácora del cliente apenas se obtenga.

## 3. Entorno seguro (no negociable, todos los clientes)

- Nunca escribir sobre la BD real. Trabajar sobre una copia de prueba,
  recreable con `DROP DATABASE` + `CREATE DATABASE ... TEMPLATE <db_real>`.
- Detener el contenedor de Odoo del cliente antes de cualquier SQL directo
  sobre tablas que sirve en vivo; confirmar `SELECT pid FROM
  pg_stat_activity WHERE datname='<db>'` vacío antes de tocar nada.
  Reiniciar y confirmar `HTTP service`/`Worker WorkerHTTP` vivos en los
  logs antes de dar el paso por bueno.
- Nunca usar `.write()` del ORM sobre líneas contables durante la migración
  (dispara `_sync_dynamic_lines` en cascada, puede dejar campos en `NULL`
  sin ningún error visible). Todo el pipeline es SQL directo vía
  `psycopg2`. Si hace falta el cálculo real del motor de Odoo, replicarlo en
  Python puro (leer, `.filtered()`, `.mapped()`, funciones utilitarias) y
  terminar con `env.cr.rollback()` -- nunca asignar un campo del recordset,
  ni "para limpiar" algo antes de calcular: cualquier asignación dispara un
  `write()` real.
- `UPDATE`s sobre la tabla completa de líneas contables van en lotes por
  rango de `id` (`BATCH_SIZE`) -- un solo `UPDATE` sobre cientos de miles de
  filas puede crashear Postgres por memoria.

## 4. El pipeline y el orden

**Desde 2026-09-23, `run.py all` es UNA SOLA corrida de ~25-26 pasos** --
ya no se detiene en la contabilidad obligatoria. Orden canónico completo:
contabilidad (`snapshot → detect → repair → swap → fix_rates →
fix_headers → fix_product_lines → fix_product_costs → fix_invoice_currency
→ fix_reconciliation → fix_invoice_rounding_balance →
fix_entry_rounding_balance`) → ventas/compras (`fix_sale_order_currency →
fix_purchase_order_currency → fix_sale_purchase_rates`) → valoración de
inventario (`fix_stock_valuation_currency`) → retenciones/analítica/landed
costs/IGTF → `remaining_value` (formula/swap/retroactivos) → `verify` →
`report_unresolved_gaps` (reporta, no modifica). El pedido del cliente de
"que no se salte nada sin decirlo" es lo que motivó esto -- **el objetivo
es que un cliente nuevo corra `run.py all` una sola vez y reciba, al
final, un reporte explícito de todo lo que quedó sin resolver**, en vez de
tener que acordarse de invocar 15 scripts sueltos.

`fix_sale_order_currency`/`fix_purchase_order_currency` (ver sección 2
punto 4) SI dependen de una decisión de negocio del cliente -- si la
respuesta es "sí, igual que las facturas", van dentro de `ALL_STEPS`; si
es "no" o "todavía no sé", se sacan de la lista para ese cliente. No
asumir que la respuesta de Proalca (sí) aplica al cliente nuevo. Siguen el
mismo principio de anclar en el "alterno" ya calculado en vez de
recomputar con una fórmula propia -- verificar primero, igual que se hizo
con `fix_invoice_currency`, que `foreign_subtotal ≈ price_subtotal *
foreign_rate` (multiplicación directa) antes de asumir que es seguro
usarlo como fuente.

**`report_unresolved_gaps()` (paso final) es el patrón a replicar con
cualquier cliente nuevo:** no modifica nada, solo cuenta y lista al final
de la corrida todo lo que se dejó sin resolver a propósito (basura sin
fuente confiable, asientos manuales sospechosos, capas de inventario sin
dato) -- así "no tocar" nunca es lo mismo que "no decirle al cliente".
Copiar esta idea aunque los gaps concretos de Proalca no apliquen al
cliente nuevo.

**ANTES de confiar en cualquier conteo de "basura" que reporte `detect()`
para un cliente nuevo, aplicar la sección 4c de METODOLOGIA.md** (detectar
a nivel de ASIENTO, no de línea aislada) -- hallazgo grave de Proalca
(2026-09-23, ver más abajo): el 96-99% de lo que los patrones B/C
marcaban como corrupción resultó pertenecer a asientos que YA cuadraban
en la moneda alterna desde el origen (asientos de "cuadre"/consolidación
con una línea ancla grande + muchas líneas chicas). **A la fecha de esta
nota, el código de `repair()` en el template todavía NO implementa la
corrección a nivel de asiento** -- quedó pausado a pedido del cliente de
Proalca mientras valida el enfoque correcto. Si el cliente nuevo tiene
volumen suficiente para sospechar el mismo patrón, medir esto (ver query
en METODOLOGIA.md 4c) antes de reportarle un número de "líneas corruptas"
-- y considerar implementar el fix de una vez para ese cliente en lugar de
heredar el mismo hueco.

Antes de saltar o reordenar un paso (el cliente lo va a pedir en algún
momento): preguntar explícitamente *¿qué campos escribe este paso, y algún
paso que ya corrió los lee para calcular otra cosa?* Si sí, saltar el orden
deja datos derivados obsoletos sin ningún error visible (pasó con
`fix_invoice_currency`/`fix_reconciliation` en Proalca -- ver METODOLOGIA.md
sección 2 para el caso completo).

Si hay que re-correr un paso ya ejecutado para arreglar un problema de
orden: **leer el SQL primero y clasificar cada UPDATE** en idempotente
(reset-y-recalculo, o guardado por condición tipo `CASE WHEN currency_id=...`)
vs no idempotente (una asignación sin guarda que compone en cada corrida,
tipo `amount = amount * tasa`). Nunca re-correr un paso completo si tiene
alguna parte no idempotente -- escribir un script puntual que reproduzca
solo las partes seguras.

## 5. Restricciones de Postgres que fuerzan una decisión

`account_move_line_check_credit_debit` (`credit*debit=0`) y
`account_move_line_check_amount_currency_balance_sign` son restricciones
reales de Odoo que pueden chocar con "no toques nada" apenas se haga
`swap()`. Cuando choque, presentar SIEMPRE dos opciones al cliente via
`AskUserQuestion`, nunca decidir solo:

1. **Netear/consolidar** (preserva el neto exacto, no inventa ni descarta
   plata) -- default, seguro, suficiente si solo importa el balance neto.
2. **Eliminar la restricción** (`ALTER TABLE ... DROP CONSTRAINT`) y escribir
   los valores brutos originales tal cual -- necesario si el cliente audita
   también el detalle bruto (pasó en Proalca: auditó totales mensuales de
   débito/crédito por separado y encontró las líneas neteadas). Avisar que
   Odoo mismo no soporta nativamente una línea con débito Y crédito a la vez
   -- puede haber reportes/vistas que asuman exclusividad.

## 5b. Antes de actualizar módulos (`-u all` o similar) sobre data ya migrada

Casi todo lo que este pipeline escribe es SQL directo sobre campos que en
operación normal calcula un `_compute` del módulo -- un `-u all` reactiva ese
motor y, si algún módulo trae un script de migración que fuerza recompute
sobre `account.move.line`/`account.partial.reconcile`, puede pisar los
montos migrados con un recálculo hecho con la tasa de HOY. **Nunca correr
`-u all` directo sobre la BD de prueba que el cliente está validando.**
Probar primero en una copia desechable:

1. Detener el contenedor, crear una copia nueva (`CREATE DATABASE ...
   TEMPLATE <db_buena>`), reiniciar el contenedor para que la BD buena siga
   disponible.
2. Copiar el filestore a la copia nueva (ver nota debajo -- si no, va a dar
   error 500 al pedir cualquier asset/adjunto).
3. Correr `docker exec <contenedor> odoo -d <copia> -u all --stop-after-init
   --no-http --logfile=/tmp/upgrade_all.log` (puede tardar varios minutos
   con muchos módulos custom -- correr en background).
4. Revisar el log por tracebacks reales (no solo warnings -- los warnings de
   "unable to add constraint" sobre las restricciones que se quitaron a
   propósito son esperados y no bloquean nada).
5. Repetir la comparación mes a mes de la sección 6 entre la copia
   actualizada y la BD buena sin actualizar. Si hay diferencia, el
   `-u all` sí está distorsionando algo -- identificar qué módulo trae el
   script de migración responsable antes de tocar la BD real del cliente.

Nota de infraestructura: si el Postgres compartido rechaza la conexión con
"the database system is not yet accepting connections / Consistent recovery
state has not been yet reached", es un blip de checkpoint/recovery del
servidor compartido, no un error nuestro -- reintentar en unos segundos y
confirmar con `docker logs <pg> --tail 20` que dice "ready to accept
connections" antes de reintentar.

Al clonar cualquier BD con `CREATE DATABASE ... TEMPLATE`, copiar también el
filestore -- ver METODOLOGIA.md sección 4b.

## 6. Verificación obligatoria antes de entregar

`verify()` (diferencia débito-crédito global) no basta -- no detecta
diferencias que se cancelan en el agregado. Comparar SIEMPRE mes a mes,
antes de avisarle al cliente que la BD de prueba está lista:

```sql
-- BD migrada (ya en la moneda nueva)
SELECT to_char(m.date,'YYYY-MM') mes, sum(l.debit), sum(l.credit)
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
WHERE l.company_id=<ID> AND m.state='posted' GROUP BY 1 ORDER BY 1;

-- BD original intacta (columna alterno, en la misma moneda antes de tocar nada)
SELECT to_char(m.date,'YYYY-MM') mes, sum(l.foreign_debit), sum(l.foreign_credit)
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
WHERE l.company_id=<ID> AND m.state='posted' GROUP BY 1 ORDER BY 1;
```

Si hay diferencia en algún mes: exportar ambos lados a CSV por `id` y hacer
diff en Python en vez de adivinar por el monto -- en los dos casos reales de
Proalca esto identificó la línea exacta en minutos.

## 7. Cierre de cada sesión con un cliente

1. Actualizar la bitácora del cliente con cada decisión tomada y su porqué
   (igual formato que `BITACORA_EJECUCION.md`/`LECCIONES.md` de Proalca).
2. Si algo generalizable no estaba cubierto por este skill o por
   `METODOLOGIA.md`, actualizar ambos antes de cerrar -- este skill crece
   con cada cliente, no es un documento fijo.
3. Confirmar el estado del contenedor (arriba o abajo, según lo que el
   usuario necesite a continuación) antes de terminar.
