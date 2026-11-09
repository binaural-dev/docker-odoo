# INCIDENT — T-200 · Crítica · «¡No podemos vender!»

| | |
|---|---|
| Cliente | Comercial Los Andes C.A. (ficticia) |
| Módulo | `sale_commission` (1.1.0 → **1.1.1**) |
| Síntoma | Desde el despliegue de las 12:00 m., ningún vendedor puede confirmar pedidos (error rojo). El gerente sí puede. |
| Rama | `hotfix/T-200` |
| Commits | `9a95e9d` [TEST] prueba que reproduce · `3dbd7a3` [FIX] corrección (tramo A) · `d763732` [TEST] + `5bdec31` [FIX] porcentaje del vendedor (tramo C) · `367c717` script de solo lectura (tramo C) |
| Commit que introdujo el error | `3f4d73f` [FEAT] sale_commission: porcentaje de comisión por categoría de producto |

## 1. Cómo se reproduce

**En la interfaz**

1. Con un usuario que solo tenga *Ventas › Usuario: solo sus documentos* (`sales_team.group_sale_salesman`),
   crear una cotización propia con cualquier producto.
2. Pulsar **Confirmar**.
3. Aparece el error:

   ```
   You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
   This operation is allowed for the following groups:
       - Sales/Administrator
   ```

4. La misma cotización, confirmada por un usuario *Ventas › Administrador*, se confirma sin problema.

**En las pruebas** (corren con el usuario vendedor, no como administrador):

```bash
./odoo test prueba-tecnica sale_commission -d t200
```

Antes de la corrección (`9a95e9d`): `0 failed, 2 error(s) of 8 tests`. Fallan
`test_t200_salesman_confirms_own_order` y `test_t200_salesman_confirm_uses_category_rule` con:

```
File ".../sale_commission/models/sale_order.py", line 10, in action_confirm
    line.commission_percent = line._get_commission_percent()
File ".../sale_commission/models/sale_order_line.py", line 28, in _get_commission_percent
    rules = self.env["sale.commission.rule"].search([
...
odoo.exceptions.AccessError: You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
```

## 2. Causa raíz

La actualización desplegada a las 12:00 m. (commit `3f4d73f`, «porcentaje de comisión por categoría de
producto») creó el modelo `sale.commission.rule` y cambió cómo se fija la comisión:

- `sale.order.action_confirm()` ahora llama a `sale.order.line._get_commission_percent()`, que hace un
  `search()` sobre `sale.commission.rule` **con el usuario que confirma**.
- En `security/ir.model.access.csv` el modelo nuevo solo recibió acceso para
  `sales_team.group_sale_manager`. Un vendedor no tiene ni lectura, así que el `search()` lanza
  `AccessError` y toda la confirmación se revierte.
- El gerente sí tiene acceso; por eso «con el usuario del gerente funciona».

No es un problema de datos ni de configuración del cliente: es un permiso que faltó en el código.

## 3. Corrección

Una línea en `security/ir.model.access.csv`:

```csv
access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
```

- **Solo lectura** para el vendedor: puede leer los porcentajes que el sistema necesita para calcular su
  comisión, pero no puede crear, modificar ni borrar reglas (lo cubre una prueba).
- **Sin `sudo()`** y sin darle al vendedor el grupo del gerente. Se descartó `sudo()` en
  `_get_commission_percent()` porque esconde el problema en vez de declarar quién puede leer qué, y cualquier
  otra lectura de reglas (por ejemplo `action_recompute_commissions`) seguiría fallando.
- Que el vendedor pueda leer los porcentajes por categoría es aceptable: son las condiciones de su propia
  comisión. Si el cliente quisiera ocultarlos, habría que mover el cálculo a un método con `sudo()`
  justificado y documentado; queda como pregunta para el cliente, no para el hotfix.
- Se sube la versión a `1.1.1` para que la actualización quede registrada.

No se tocó la lógica del módulo: es producción y el cambio mínimo es el que menos riesgo tiene.

## 4. Pruebas

Nuevas en `tests/test_sale_commission.py`, todas con `with_user()`:

| Prueba | Qué demuestra | Antes | Después |
|---|---|---|---|
| `test_t200_salesman_confirms_own_order` | El vendedor crea y confirma su pedido; la comisión es la suya (5 %) | ❌ AccessError | ✅ |
| `test_t200_salesman_confirm_uses_category_rule` | Como vendedor, se aplica la regla de la categoría (8 %) | ❌ AccessError | ✅ |
| `test_t200_manager_still_confirms` | El gerente sigue confirmando pedidos de un vendedor | ✅ | ✅ |
| `test_t200_salesman_cannot_manage_rules` | El vendedor **no** puede modificar, crear ni borrar reglas | ✅ | ✅ |

Después de la corrección (`3dbd7a3`): `0 failed, 0 error(s) of 8 tests`.

## 5. Contención, despliegue y comunicación (tramo B)

### 5.1 Primeros 15 minutos (antes de tener la corrección)

| Minuto | Acción |
|---|---|
| 0–2 | Responder el ticket: «Recibido, lo estamos revisando ahora; le escribimos antes de las 6:15 p.m.». Así el cliente sabe que alguien lo atiende. |
| 2–7 | Reproducir con un usuario vendedor de prueba y leer el registro del servidor: `AccessError` sobre `sale.commission.rule`, «permitido para Ventas/Administrador». Con eso ya se sabe que **es un permiso que falta**, no un problema de datos. |
| 7–12 | **Contención:** en producción, como administrador, *Ajustes › Técnico › Seguridad › Derechos de acceso › Nuevo*: nombre `T-200 contención (borrar al desplegar 1.1.1)`, modelo *Comisión por categoría de producto*, grupo *Ventas / Usuario: solo sus documentos*, **solo Leer** marcado. |
| 12–15 | Verificar con un vendedor real o de prueba que confirma un pedido. Pedirle al gerente que **deje de confirmar pedidos de otros** y avisar al cliente. |

**Por qué esta contención:** hace lo mismo que la corrección definitiva, pero como dato y no como código. No
hay que desplegar ni reiniciar, toma efecto al instante y **se revierte borrando un registro**.

**Riesgos y cómo se controlan:**

- Es un cambio manual en producción, fuera del código. Puede quedar olvidado o duplicado cuando se despliegue
  la 1.1.1, que trae su propio permiso. Por eso lleva un nombre explícito y borrarlo es un paso del despliegue
  (5.3). Mientras existan los dos, no hay conflicto: los permisos se suman.
- Los vendedores pueden **leer** los porcentajes de comisión por categoría. Es la misma exposición que deja la
  corrección definitiva y no da escritura.
- **No corrige el segundo defecto** (sección 6): si el gerente confirma pedidos ajenos, la comisión toma el
  porcentaje del gerente. Por eso se le pide que no lo haga hasta el despliegue. Cuando cada vendedor confirma
  lo suyo, el porcentaje es el correcto.
- Se aplica directo en producción sin pasar por pruebas automáticas. Se mitiga verificando de inmediato con
  un vendedor y anotando la hora del cambio.

**Alternativas descartadas:**

- Darles a los vendedores el grupo del gerente: verían y modificarían todo (todos los pedidos, reglas,
  configuración), más permisos de los necesarios.
- Desinstalar el módulo o volver a la 1.0.0: el cambio de esquema (modelo nuevo, campo calculado que pasó a
  ser normal) arriesga datos, y es más lento y menos reversible.
- Que el gerente siga confirmando todo el sábado: es un cuello de botella el día de más ventas y sigue
  generando comisiones con el porcentaje equivocado.

### 5.2 Qué commit introdujo el error y por qué pasó la revisión

El historial del módulo tiene solo dos commits antes del incidente, así que no hizo falta `git bisect`.
Bastó con preguntarle a `git log` qué commit tocó cada pieza involucrada:

```bash
$ git log --oneline -- src/custom/prueba-tecnica/sale_commission/security/ir.model.access.csv
3f4d73f [FEAT] sale_commission: porcentaje de comisión por categoría de producto
ad51040 [ADD] sale_commission: comisión del vendedor por línea y análisis mensual

$ git log --oneline -S "_get_commission_percent" -- src/custom/prueba-tecnica/sale_commission
3f4d73f [FEAT] sale_commission: porcentaje de comisión por categoría de producto

$ git log --oneline -S "self.env.user.commission_percent" -- src/custom/prueba-tecnica/sale_commission
3f4d73f [FEAT] sale_commission: porcentaje de comisión por categoría de producto
```

Con un historial más largo, la prueba nueva sirve para `git bisect run`: cada paso copia
`tests/test_sale_commission.py` de `hotfix/T-200` y corre `./odoo test ... --tags /sale_commission:TestSaleCommission.test_t200_salesman_confirms_own_order`.
El primer commit donde falla es el culpable.

**Commit culpable: `3f4d73f`.** Agrega el modelo `sale.commission.rule`, hace que `action_confirm()` lo lea
y le da acceso **solo al gerente**. Además cambia el respaldo al porcentaje de `self.env.user`.

**Por qué pasó la revisión:**

1. **El mismo commit debilitó la prueba que lo habría detectado.** Antes, la prueba creaba el pedido como
   vendedor (`with_user(user).create(...)`); el commit le quitó el `with_user()`. Desde entonces todo corre
   como administrador, y el administrador se salta los derechos de acceso. Las pruebas quedaron en verde.
2. **El fixture escondió el segundo defecto:** el commit agrega `cls.env.user.commission_percent = 5.0`, el
   mismo valor del vendedor. Así, usar el porcentaje de quien confirma o el del vendedor da igual en la prueba.
3. El commit mezcla funcionalidad, vistas, seguridad y cambios a pruebas (10 archivos). Un cambio que
   **debilita una prueba existente** pasa desapercibido entre tanto contenido nuevo.
4. Nadie probó a mano con un usuario vendedor antes del despliegue, y se desplegó un viernes a mediodía, antes
   del día de más ventas.

### 5.3 Despliegue de la corrección y verificación en producción

Módulo a actualizar: **`sale_commission` (1.1.0 → 1.1.1)**. Cambia el CSV de permisos y un archivo Python,
así que hace falta **actualizar el módulo y reiniciar** Odoo.

1. Respaldar la base de producción antes de tocar nada (`scripts/odoo_backup` del repo, o `pg_dump` + filestore).
2. Llevar `hotfix/T-200` (ya aprobado en el PR) a la rama que usa producción y bajar el código en el servidor.
3. Actualizar el módulo y reiniciar la instancia:

   ```bash
   ./odoo update <instancia> -d <base> -m sale_commission
   ./odoo restart <instancia>
   ```

4. Borrar el derecho de acceso manual `T-200 contención (borrar al desplegar 1.1.1)`.
5. Verificar:
   - *Aplicaciones*: `sale_commission` en versión **1.1.1**.
   - *Ajustes › Técnico › Derechos de acceso*, modelo *Comisión por categoría de producto*: queda
     `sale.commission.rule.salesman` (solo lectura) y ya no está el manual.
   - Con un **vendedor**: crear y confirmar una cotización propia. Se confirma y la comisión de la línea es la
     de su categoría o la del vendedor.
   - Con el **gerente**: confirmar un pedido de un vendedor. Funciona y la comisión es la **del vendedor**.
   - El registro del servidor no muestra `AccessError` desde la hora del despliegue.
   - El script de la sección 6, corrido con la hora del despliegue de la 1.1.1, no devuelve líneas nuevas.
6. Avisar al cliente y dejar el ticket en observación hasta el sábado a mediodía.

### 5.4 Mensaje al cliente

> Buenas tardes. Ya encontramos la causa: la actualización de hoy al mediodía dejó a los vendedores sin un
> permiso que necesitan para confirmar pedidos. Ya se lo devolvimos y comprobamos que un vendedor puede
> confirmar normalmente, así que mañana pueden vender sin depender del gerente. Mientras tanto, le pedimos al
> gerente que no confirme pedidos de otros vendedores. Algunas comisiones de los pedidos que él confirmó esta
> tarde pueden haber quedado mal calculadas: les enviaremos la lista y las corregiremos con su aprobación.

## 6. Impacto en los datos y prevención (tramo C)

### 6.1 ¿Quedaron datos incorrectos?

**Sí.** Además del permiso, `3f4d73f` cambió de dónde sale el porcentaje cuando la categoría del producto no
tiene regla:

```python
return self.env.user.commission_percent        # 1.1.0: el de QUIEN CONFIRMA
return self.order_id.user_id.commission_percent # 1.0.0 y 1.1.1: el del VENDEDOR del pedido
```

Esta tarde el gerente confirmó los pedidos de todos, así que **las líneas sin regla de categoría quedaron con
el porcentaje del gerente**. El vendedor del pedido no cambió (el análisis de comisiones sigue atribuyéndolas
al vendedor correcto), pero el **monto** está mal: más alto o más bajo según el porcentaje del gerente. Las
líneas con regla de categoría no se ven afectadas, porque la regla no depende de quién confirma.

Hay un segundo riesgo: que el gerente se haya **asignado** pedidos ajenos (cambiando el vendedor) para
confirmarlos. En ese caso la comisión queda a nombre del gerente, es decir, de **quien no corresponde**.

La corrección es la prueba `test_t200_manager_confirms_uses_salesman_percent`, que fallaba con
`12.0 != 5.0`, y el commit `5bdec31`, que vuelve a usar `order_id.user_id` (una línea, igual que la 1.0.0).
Va en el mismo hotfix para que el problema no se siga generando.

### 6.2 Script de solo lectura: `scripts/t200_affected_records.sql`

```bash
# Desde el servidor (servicio de Postgres de la instancia). since = despliegue de la 1.1.0 en UTC
# (12:00 m. hora de Venezuela = 16:00 UTC).
docker exec -i <contenedor-db> psql -U odoo -d <base> -v since='2026-10-16 16:00:00' \
    < src/custom/prueba-tecnica/sale_commission/scripts/t200_affected_records.sql
```

- Corre dentro de `BEGIN TRANSACTION READ ONLY ... ROLLBACK`: Postgres **rechaza** cualquier escritura
  (`ERROR: cannot execute UPDATE in a read-only transaction`). Sin el parámetro `since` no ejecuta nada.
- **Sección 1:** líneas de pedidos confirmados desde `since` cuyo porcentaje guardado no es el que corresponde
  (regla más específica de la categoría o, si no hay, el porcentaje del vendedor del pedido). Muestra quién
  confirmó según el chatter, la comisión guardada, la correcta y la diferencia.
- **Sección 2:** pedidos a los que se les cambió el vendedor desde `since`: quién lo cambió, el vendedor
  anterior y el nuevo.

**Cómo se probó.** `scripts/t200_seed_incident.py` simula la tarde del incidente en una base de pruebas:
3 usuarios (vendedor A 5 %, vendedor B 3 %, gerente 12 %), una categoría con regla del 8 % y otra sin regla,
y 6 pedidos con un caso de cada tipo. Resultado sobre esa base:

| Pedido | Caso | ¿Lo lista? |
|---|---|---|
| S00001 | El vendedor confirma lo suyo | No (correcto) |
| S00002 | El gerente confirma, sin regla: 12 % en vez de 5 % | **Sección 1** (diferencia −7,00) |
| S00003 | El gerente confirma, con regla 8 % | No (correcto) |
| S00004 | Pedido mixto: línea sin regla al 12 % en vez de 3 %, línea con regla al 8 % | **Sección 1**, solo la línea sin regla (−9,00) |
| S00005 | El gerente se asigna el pedido del vendedor A y lo confirma | **Sección 2** |
| S00006 | Cotización sin confirmar | No |

Una suma de control de `sale_order_line` (cantidad, suma de porcentajes, suma de comisiones y último
`write_date`) dio el mismo resultado antes y después de correr el script.

**Limitaciones:**

- Si una regla de categoría cambió **después** de confirmar un pedido, esa línea aparece con el motivo «con
  regla: … (revisar a mano)». No es un error del incidente, y el script no tiene forma de distinguirlo.
- «Confirmado por» sale del chatter (el último cambio de estado). Si a alguien le desactivaron el
  seguimiento, aparece vacío.
- `since` debe estar en UTC, porque Odoo guarda las fechas en UTC.

### 6.3 Plan para corregir los datos

Se ejecuta **después** de desplegar la 1.1.1, para que no se generen registros nuevos con el error, y en
horario sin operación.

1. **Respaldo** de la base. Anotar la hora.
2. **Listar:** correr el script con `since` = hora del despliegue de la 1.1.0, guardar la salida (`--csv`) y
   enviarla al cliente (administración y gerente de ventas).
3. **Validar con el cliente** antes de cambiar nada:
   - ¿Ya se pagó o se cerró alguna comisión de esos pedidos? Si sí, el ajuste va por nómina o pago, no
     editando el pedido.
   - Sección 2: ¿el cambio de vendedor fue intencional? Solo se revierten los que el cliente confirme.
4. **Corregir la sección 2** (si aplica): en cada pedido confirmado por el cliente, volver a poner al
   vendedor anterior desde la interfaz. Así queda registrado en el chatter.
5. **Corregir la sección 1:** en el REPL de Odoo (`./odoo shell -d <base> <instancia> shell`), como administrador, solo sobre las
   líneas listadas con motivo «sin regla» y aprobadas:

   ```python
   line_ids = [...]  # linea_id aprobados, copiados del CSV
   lines = env["sale.order.line"].browse(line_ids).exists()
   for line in lines:
       old = line.commission_percent
       new = line._get_commission_percent()  # 1.1.1: regla de categoría o porcentaje del vendedor del pedido
       print(line.order_id.name, line.id, old, "->", new)
       line.commission_percent = new  # commission_amount se recalcula solo
       line.order_id.message_post(body=f"T-200: comisión de la línea {line.id} corregida de {old} % a {new} %.")
   # Revisar lo impreso y recién ahí:
   env.cr.commit()  # (si algo no cuadra: env.cr.rollback())
   ```

   No se usa el botón *Recalcular comisiones*: tiene su propio defecto (6.4) y recalcularía también líneas
   que están bien.
6. **Verificar:** volver a correr el script. La sección 1 no debe mostrar líneas «sin regla». Comparar el
   total del análisis de comisiones por vendedor con lo que el cliente espera.
7. **Reversión:** si algo sale mal, restaurar el respaldo del paso 1. Si ya hubo operación después, revertir
   solo las líneas corregidas usando los valores `pct_guardado` del CSV del paso 2.

### 6.4 ¿Existe el mismo patrón en otra parte del módulo?

El patrón es **código que depende de quién lo ejecuta** (sus permisos o sus datos) en vez del registro que
procesa. Revisión del módulo completo:

| Dónde | Hallazgo | Acción |
|---|---|---|
| `sale_order_line._get_commission_percent()` | Lectura de `sale.commission.rule` con el usuario actual (sin permiso para vendedores) | Corregido (`3dbd7a3`) |
| `sale_order_line._get_commission_percent()` | Respaldo con `self.env.user.commission_percent` | Corregido (`5bdec31`) |
| `sale_order.action_recompute_commissions()` | Mismo acceso a `sale.commission.rule` con el usuario actual | Queda resuelto con el permiso de lectura |
| `sale_order.action_recompute_commissions()` | **Otra lógica distinta**: busca la regla solo por categoría exacta (ignora categorías padre y compañía), mientras que la confirmación usa la más específica con `parent_of`. Además, el botón lo ve cualquier usuario con el pedido confirmado, también el vendedor. | **No se toca en el hotfix** porque no bloquea la operación. Ticket aparte: que use `_get_commission_percent()` y que el botón sea solo para el gerente (`groups="sales_team.group_sale_manager"`). Mientras tanto, no usar el botón. |
| `sale.commission.rule` | Tiene `company_id`, pero no hay regla de registro multicompañía: un vendedor puede leer reglas de otra compañía (solo lectura). El cálculo sí filtra por compañía. | Ticket aparte, baja prioridad. |
| `product_category.commission_percent` | `groups="sales_team.group_sale_manager"` y el inverso crea reglas: solo el gerente lo ve y edita. | Correcto. |
| `sale.commission.report` + reglas de registro | El vendedor ve solo lo suyo (`user_id = user.id`); probado en `test_salesman_report_only_own`. | Correcto. |

### 6.5 Prevención: qué habría evitado que llegara al cliente

1. **Regla de pruebas: los flujos de negocio se prueban con el usuario de menor permiso que los usa.**
   Confirmar un pedido lo hace un vendedor, así que la prueba confirma con
   `with_user(<usuario con solo group_sale_salesman>)`. Ejecutar como administrador se salta los derechos de
   acceso y no prueba nada sobre permisos. Aplicado aquí: las pruebas `test_t200_*` (5 en total).
2. **Regla de revisión: un PR que debilita una prueba existente necesita justificación explícita.** Quitar
   un `with_user()`, borrar una aserción o cambiar un valor esperado se revisa primero, antes que el código
   nuevo. En la plantilla del PR: «¿Modifica pruebas existentes? ¿Por qué?».
3. **Checklist de revisión para modelos nuevos:** «¿Quién ejecuta el código que lee o escribe este modelo?»
   Cada grupo que pasa por ese flujo necesita su línea en `ir.model.access.csv`. Además, buscar
   `self.env.user` en cálculos de negocio: casi siempre debe ser un campo del registro (`order.user_id`,
   `company_id`…).
4. **CI:** correr `./odoo test <instancia> <módulos>` en cada PR y bloquear el merge si falla.
5. **Despliegue:** antes de pasar a producción, una prueba manual en staging con un usuario de cada rol
   (vendedor y gerente) del flujo principal. No desplegar viernes por la tarde ni antes del día pico del
   cliente sin esa verificación y sin alguien de guardia.
