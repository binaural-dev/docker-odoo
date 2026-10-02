---
name: commit-message
description: Construye el mensaje de commit siguiendo el estandar corporativo (PDF "Git - Ramas y Commits" + plantilla ~/.gitmessage), adaptado al patron real observado en los commits del usuario. Usar cuando el usuario pida crear un commit, redactar el mensaje de commit, o pregunte por el formato/estandar de commits o ramas del proyecto.
---

# commit-message

Construye mensajes de commit para cualquier repositorio de este proyecto (repo principal `docker-odoo`, cualquier custom bajo `src/custom/*`, o los submodulos `odoo-venezuela`/`integra-addons`/`third-party-addons`) siguiendo el estandar corporativo documentado en `Git - Ramas y Commits.pdf` y el patron real confirmado en el historial de commits de RogerVBinaural.

**Nota importante**: la plantilla oficial de git (`~/.gitmessage`, resolver via `git config --get commit.template`, nunca hardcodear la ruta) define el *esqueleto* del mensaje, pero el uso real en el historial difiere en un punto clave (ver "Estructura del cuerpo" abajo). Este skill sigue el **patron real**, no la plantilla literal.

## 1. Estandar de tags para commits

### Core (uso frecuente, del PDF corporativo)
- `FIX` — correccion de errores
- `HOTFIX` — correccion urgente aplicada sobre release
- `FEAT` — nueva funcionalidad (crea algo que no existia, cambia el flujo funcional, impacto visible, requiere QA completo, normalmente asociado a **tarea**)
- `REF` — refactorizacion sin cambio funcional
- `IMP` — mejora incremental (no crea funcionalidad nueva, ajusta algo existente, impacto pequeño/moderado, no requiere analisis funcional profundo, normalmente asociado a **ticket**)
- `DEPLOY` — cambios de despliegue, CI/CD, scripts
- `CHORE` — mantenimiento (librerias, housekeeping, ajustes tecnicos)
- `DOCS` — cambios exclusivamente en documentacion
- `TEST` — adicion o correccion de pruebas
- `STYLE` — formato de codigo sin impacto funcional

### Extended (casos especificos Odoo, del PDF corporativo)
- `ADD` — creacion de un nuevo modulo
- `REM` — eliminacion de modulos o recursos
- `MOV` — movimiento de archivos
- `REV` — revertir un commit
- `REL` — commit de release (trimestral o semanal)
- `MERGE` — merge commits
- `CLA` — firma de contribuciones
- `I18N` — cambios de traducciones
- `PERF` — mejoras de rendimiento
- `CLN` — limpieza de codigo
- `LINT` — linter

### Extension propia (no esta en el PDF, pero se usa en la practica — confirmada con el usuario)
- `MIG` — migracion/homologacion de un modulo custom del cliente hacia odoo-venezuela/integra-addons (uso muy frecuente en el historial real, ej. `[MIG] l10n_ve_base: Correccion de traduccion`)

**Nota**: `IMP` NUNCA es un tipo de rama, solo de commit. Las mejoras incrementales viven dentro de ramas `feat/`, `chore/` o `perf/` segun el caso.

### Que tags van en cada tipo de rama
| Tipo de rama | Tags esperados |
|---|---|
| `hotfix` | `HOTFIX`, `FIX`, `TEST`, `REL` |
| `fix` | `FIX`, `TEST`, `IMP` |
| `feat` | `FEAT`, `IMP`, `REF`, `TEST`, `DOCS` |
| `refactor` | `REF`, `CLN`, `STYLE`, `TEST` |
| `chore` | `CHORE`, `IMP`, `STYLE`, `LINT`, `TEST`, `CLA` |
| `deploy` | `DEPLOY`, `CHORE`, `DOCS` |
| `docs` | `DOCS` |
| `test` | `TEST` |
| `style` | `STYLE`, `LINT` |
| `add` | `ADD`, `FEAT` |
| `remove` | `REM` |
| `perf` | `PERF`, `IMP`, `TEST` |
| `i18n` | `I18N` |

Si el commit se hace sobre una rama con un tipo declarado en su nombre (ver seccion 2), el TAG propuesto debe ser coherente con esta tabla; si no calza, preguntar al usuario antes de asumir.

## 2. Convencion de nombres de ramas (contexto, no se crea la rama automaticamente)

```
<origen>_<tipo>-<tipo_asignacion>_<id_ticket_o_tarea>_<nombre_corto_en_ingles>
```

- **origen**: `rls` (parte de release), `stg` (parte de staging), `<hash-corto>` (parte de un commit especifico), `17.0`/`l10nve_17.0`/etc. (parte de una rama oficial), `maint_17.0.1`/`maint_l10nve_17.0.1`/etc. (parte de mantenimiento trimestral)
- **tipo**: `hotfix`, `fix`, `feat`, `refactor`, `deploy`, `chore`, `docs`, `test`, `style`, `add`, `remove`, `perf`, `i18n`
- **tipo_asignacion**: `ti` (ticket, modulo de asistencia) o `ta` (tarea, modulo de proyectos)
- **id**: numero del ticket o tarea
- **nombre_corto_en_ingles**: descripcion breve en ingles

Ejemplos reales: `2cd70432_fix-ti_14172_tax_config_views`, `maint-17.0_fix-ti_13694_foreign_residual_inconsistency`, `0fc98da1_upd-ta_75512_submodules_upd` (nota: `upd` se usa en la practica para actualizaciones de submodulos aunque no este en la lista oficial de tipos de rama).

El nombre de la rama ya trae el ticket/tarea — usar el mismo `ti`/`ta` + numero para las `References` del commit.

## 3. Formato del mensaje de commit

### Reglas obligatorias
- Redactado en **español**.
- Primera linea: `[TAG] módulo(s): descripción corta (< 50 caracteres)`, en **modo imperativo**.
- Varios modulos van separados por coma: `account, sale, stock`.
- En `References` es **obligatorio** incluir al menos un enlace a Ticket o Tarea.
- El commit debe ser claro, trazable y auditable — la descripcion larga explica el **por que**, no el que (eso ya lo dice el diff).

### Estructura del cuerpo (orden logico a seguir, SIN encabezados literales)

A diferencia de la plantilla literal de `~/.gitmessage` (que sugiere repetir la descripcion corta como primera linea del cuerpo), el cuerpo sigue un **orden logico** de 4 ideas — resumen, error, causa, solucion — pero redactadas como **prosa natural en parrafos**, igual que los ejemplos reales de la seccion 6. Nunca escribir literalmente "Resumen:", "Error:", "Causa:" o "Solucion:" como encabezados; esas palabras son una guia interna para ordenar las ideas, no texto que va en el commit.

```
[TAG] módulo(s): descripción corta

<Ticket|Tarea> <numero>: <título/descripción del ticket o tarea>

<Parrafo(s) en prosa que cubren, en este orden: que se hizo -> cual era
el error/comportamiento incorrecto -> por que ocurria (causa raiz) ->
como se soluciono tecnicamente. No hace falta que cada idea sea un
parrafo separado; se puede fusionar lo que fluya natural, como en los
ejemplos reales>

<Opcional: parrafo adicional de "Nota" SIN el encabezado "Nota:" — solo
si hay algo relevante que agregar y que no quedo cubierto arriba. Si el
patron del historial usa la palabra "Nota:" como introduccion de un
parrafo de advertencia, se puede mantener porque asi aparece en los
commits reales, pero no es un titulo de seccion obligatorio>

References:
- Ticket: <URL completa o vacío>
- Tarea: <URL completa o vacío>
- PR: <URL o vacío>
- Otros: <URL o vacío, se puede omitir la línea si no aplica>
```

Puntos clave de este patron:
- La segunda linea del cuerpo (primera despues del asunto) SIEMPRE es `Ticket <numero>: <titulo>` o `Tarea <numero>: <titulo>` — nunca se repite la descripcion corta como frase generica.
- El orden **resumen -> error -> causa -> solucion** es la guia por defecto para commits `FIX`/`HOTFIX`/`MIG` (tienen un error identificable). Para tags donde no aplica un "error" (ej. `FEAT`, `ADD`, `CHORE`), el orden equivalente es **resumen -> contexto/motivo -> implementacion**.
- **La nota NUNCA es obligatoria** — solo se agrega si hay algo relevante que agregar que no haya quedado cubierto en el resto del cuerpo (advertencias a consultores, casos limite, contexto para mantenimiento futuro). Preguntar al usuario si quiere agregar una; si no aplica, simplemente no se incluye ese parrafo.
- URLs completas en `References`: `https://binaural.odoo.com/odoo/my-tickets/<numero>` para Ticket, `https://binaural.odoo.com/odoo/action-341/<numero>` para Tarea.
- Si un campo de `References` claramente no aplica (ej. no hay PR aun) puede quedar vacio o incluso omitirse la linea completa (`Otros:` se omite con frecuencia) — pero Ticket o Tarea (al menos uno) es obligatorio.

## 4. Informacion necesaria para armar el mensaje

Reunir estos elementos antes de redactar. Los marcados **derivable** se obtienen del repo; los marcados **preguntar** casi nunca estan en el diff y deben pedirse al usuario (o tomarse de contexto ya dado en la conversacion) — nunca inventarlos ni poner "N/A":

1. **TAG** — *derivable (proponer) + confirmar*. Ver diccionario de la seccion 1. Confirmar siempre que haya ambiguedad (p.ej. IMP vs FEAT vs FIX), y validar coherencia con el tipo de rama si aplica (seccion 1, tabla).

2. **Modulo(s) afectado(s)** — *derivable*.
   ```bash
   git diff --staged --name-only | cut -d/ -f1 | sort -u
   ```
   Varios modulos van separados por coma.

3. **Descripcion corta** (<50 caracteres, español, modo imperativo) — *proponer a partir del diff + confirmar*. Va solo en la primera linea (asunto); NO se repite en el cuerpo.

4. **Tipo de asignacion + numero** (Ticket o Tarea) — *preguntar siempre que no se haya mencionado ya*. Determina:
   - La segunda linea del cuerpo: `Ticket <numero>: <titulo>` o `Tarea <numero>: <titulo>`
   - El campo correspondiente en `References` con la URL completa

5. **Titulo del ticket/tarea** — *preguntar si no se ha mencionado*. Es la descripcion corta del problema/pedido tal como aparece en el sistema (Odoo helpdesk o modulo de proyectos), se usa en la linea `Ticket <numero>: <titulo>`.

6. **Resumen** (que se hizo) — *derivable del diff + conversacion*. 1-2 lineas, primera idea del cuerpo en prosa (sin encabezado literal).

7. **Error/Contexto** (o **Motivo** si el tag no implica un error, ver seccion 3) — *derivable de la conversacion*. Cual era el comportamiento incorrecto o el problema/necesidad reportada.

8. **Causa** — *preguntar si no quedo explicito en la conversacion*. La causa raiz tecnica — el "por que" ocurria el problema. No inventar una causa si no se discutio.

9. **Solucion** — *derivable del diff + conversacion*. Como se resolvio tecnicamente, el cambio concreto aplicado.

10. **Nota** — *SIEMPRE preguntar si quiere agregar una, NUNCA asumir que aplica*. Es el unico elemento opcional del cuerpo: solo se agrega si hay algo relevante que no quedo cubierto en resumen/error/causa/solucion ni en el resto del commit (advertencias, casos limite, contexto para mantenimiento futuro). Si el usuario no indica una nota, simplemente no se agrega ese parrafo — nunca se fuerza.

Estos 4 elementos (6-9) se redactan como **prosa natural** siguiendo ese orden logico, sin encabezados tipo "Resumen:"/"Causa:" — ver seccion 3.

11. **PR / Otros** — *preguntar si aplica, puede quedar vacio o omitirse*.

12. **Cambios a incluir** — *derivable*. Confirmar con `git status`/`git diff --staged` que solo estan stageados los archivos relevantes, siguiendo las reglas generales de staging cuidadoso (nunca `git add -A`).

## 5. Flujo de trabajo

1. Ejecutar `git status` y `git diff --staged` (o `git diff` si nada esta stageado) para entender el cambio real.
2. **Siempre, para cualquier modulo Odoo tocado por el cambio** (carpeta con `__manifest__.py` en su raiz — aplica igual en el repo principal del cliente y en cualquier submodulo: `odoo-venezuela`/`integra-addons`/`third-party-addons`, no es un patron exclusivo de un cliente en particular): verificar si el diff ya incluye un cambio en la clave `"version"` de ese `__manifest__.py`. Si no lo incluye, incrementar el ultimo segmento de la version (patron real observado en el historial: `17.0.1.0.16` -> `17.0.1.0.17`) y agregar ese archivo a lo que se va a commitear. **Esto no requiere aprobacion separada del usuario** — se hace como parte normal de preparar el commit, igual para todos los modulos afectados si son varios. Si el formato de version de ese modulo no sigue el patron `X.Y.A.B.C` esperado (caso raro), preguntar antes de decidir el nuevo numero.
3. Derivar modulo(s) afectado(s) y proponer un TAG (validar contra el tipo de rama si el nombre de la rama actual sigue la convencion de la seccion 2).
4. Revisar la conversacion en busca de: ticket/tarea + numero + titulo, PR, y el motivo/causa raiz del cambio. Si falta algo de la seccion 4, preguntar puntualmente — no asumir.
5. Redactar el mensaje completo siguiendo el patron real de la seccion 3 (no la plantilla literal).
6. Mostrar el mensaje propuesto al usuario para su aprobacion antes de commitear.
7. Si el usuario aprueba y pidio explicitamente crear el commit, seguir el flujo estandar de git (stage de archivos especificos — incluyendo el/los `__manifest__.py` ajustados en el paso 2 —, `git commit` con el mensaje via HEREDOC, `git status` de verificacion) — nunca commitear sin peticion explicita.
8. **Siempre, inmediatamente despues del commit**: correr `pre-commit` sobre los archivos del commit, para detectar en local cualquier problema que el check de `pre-commit` en el PR marcaria de todas formas — evita tener que esperar al resultado del CI para enterarse.
   ```bash
   pre-commit run --files $(git diff-tree --no-commit-id --name-only -r HEAD)
   ```
   No importa si `pre-commit` esta instalado como git hook local o no (`.git/hooks/pre-commit` puede no existir) — el comando anterior lo ejecuta igual de forma manual sobre los archivos del commit recien creado.
   - **Todos los hooks pasan o se saltan** (por no aplicar a esos archivos): continuar normalmente hacia el paso de PR.
   - **Algun hook falla** — ya sea porque modifico archivos automaticamente (formateo/autofix) o porque marco un error sin poder corregirlo solo: **nunca corregir ni commitear automaticamente**, en ningun caso. Reportar al usuario: que hook fallo, la salida/mensaje exacto de `pre-commit`, y (si aplica) el diff que el hook ya dejo en el working tree (`git diff`) junto con cual seria la correccion pertinente para ese caso puntual. Detenerse ahi y esperar que el usuario decida — el o ella decide si se aplica la correccion, la hace de otra forma, o continua sin ella. No avanzar al paso de PR hasta que el usuario lo indique explicitamente.

## 6. Ejemplos

### Ejemplos historicos (del historial de odoo-venezuela, formato libre previo a los bloques Resumen/Error/Causa/Solucion)

Sirven para ver el tono y nivel de detalle esperado; el contenido del cuerpo en commits nuevos se organiza en bloques (seccion 3), pero el nivel de detalle tecnico es el mismo.

```
[FIX] l10n_ve_accountant: Inconsistencia en monto residual bs

Ticket 13694: Monto residual de los bs no coincide con el total del la factura

Se hizo un ajuste en el computado de foreign_amount_residual:
	-Toma las lineas de pago para calcular el total pagado (Usando monto alterno)
	-Calcula el residual usando: Total alterno - Total pagado alterno

De esta forma se evita la inconsistencia en futuras facturas.

Nota:
Esto puede generar pequeñas diferencias en facturas ya pagadas debido a que hubo facturas que se pagaron con el monto residual mal calculado,
esta inconsistencia puede seguir apareciendo en facturas anteriores al cambio, se debe mencionar esto a los consultores al momento de presentar casos con el mismo problema.

References:
- Ticket: https://binaural.odoo.com/odoo/my-tickets/13694
- Tarea:
- PR:
- Otros:
```

```
[MIG] l10n_ve_base: Correccion de traduccion

Tarea 68400: Migracion casaroda

Se encontro una insconsistencia en una traduccion mientras se realizaba la migracion
Fue necesario corregir esto y eliminar la vista para poder resolver el problema

References:
- Ticket:
- Tarea: https://binaural.odoo.com/odoo/action-341/68400
- PR:
- Otros:
```

```
[FIX] l10n_ve_iot_mf, l10n_ve_pos_mf: Error en nota de credito

Ticket 13335: Error en reembolso

Se actualizo la rama con mantenimiento.
Se hizo una correccion sobre las lineas de pago negativas, permitiendo que pasen en caso de ser notas de credito.

En l10n_ve_iot_mf se ajusto un mensaje de error inconsistente.
El mensaje mostraba problemas con la fecha de factura cuando en realidad era el numero.

References:
- Ticket: https://binaural.odoo.com/odoo/my-tickets/13335
- Tarea:
- PR:
- Otros:
```

### Ejemplo aplicando el orden resumen -> error -> causa -> solucion, en prosa (sin encabezados)

```
[FEAT] higea_stock_account: Corrige bloqueo de traslados internos por guia

Tarea <numero>: <titulo de la tarea>

Se crea el modulo higea_stock_account, adaptado desde grupokam_stock_account
para higea, corrigiendo en el proceso un bug de l10n_ve_stock_account.

Al cambiar el motivo de traslado de una guia a uno que no requiere guia de
despacho (ej. traslado entre almacenes), el campo is_dispatch_guide se
quedaba en True, forzando partner_id como obligatorio en la vista y
bloqueando la validacion de traslados internos entre almacenes. Esto
ocurria porque _compute_is_dispatch_guide en l10n_ve_stock_account es un
campo store=True cuyo compute no cubre con un else explicito el caso de
motivos que no requieren guia, por lo que el campo conservaba el ultimo
valor calculado en vez de resetearse a False.

Se sobrescribe unicamente _compute_is_dispatch_guide en
higea_stock_account, reasignando el valor en cada calculo sin dejar
ninguna rama sin cubrir, y sin tocar el store del campo para no afectar
la vista ni los campos dependientes (match_guide_dispatch_domain).

References:
- Ticket:
- Tarea: https://binaural.odoo.com/odoo/action-341/<numero>
- PR:
- Otros:
```

## 7. Caso especial: commit de bump de puntero de submodulo

Cuando el commit solo actualiza el puntero de uno o mas submodulos (`git add <submodulo...> && git commit`, sin otros cambios), el mensaje se construye distinto al flujo normal de la seccion 3. Hay dos variantes segun cuanto trae el bump: un cherry-pick puntual (7.1) o una actualizacion masiva a un tag de mantenimiento (7.2, ver skill `submodule-update`).

### 7.1 Bump puntual (cherry-pick de un commit)

Cuando el bump trae exactamente el commit de un fix puntual ya resuelto en el submodulo, se **espeja casi literal** el mensaje del commit real que ya existe dentro del submodulo, en vez de redactarse desde cero.

Reglas:
- Antes de escribir el mensaje, leer el commit real: `git log -1 --format="%B" <hash>`.
- Primera linea: la misma `[TAG] modulo(s): descripcion` del commit del submodulo — nunca un prefijo generico tipo "bump submodule X" o "trigger rebuild".
- Cuerpo: copiar el original casi tal cual, ajustando solo la referencia de ticket/tarea al ticket actual (agregando el original como relacionado si aplica).
- Cherry-pick: si el fix es cherry-pick de otro ticket, decirlo explicitamente ("Se realizo un cherry-pick de la solucion del ticket X") — nunca parafrasearlo como "se adapto la logica".
- References: no agregar una linea de referencia al submodulo/hash (ej. `Submodulo: org/repo@hash`) — el formato sigue siendo el de la seccion 3.
- El PR resultante tampoco lleva seccion de "Test plan" (ver skill `pr-create`).

Mantener el commit de bump trazable 1:1 con el commit real del submodulo permite ver desde el PR del repo principal exactamente que cambio, sin tener que ir a revisar el submodulo por separado.

### 7.2 Bump masivo (actualizacion a tag de mantenimiento)

Cuando el bump trae un tag de mantenimiento completo (potencialmente decenas de commits acumulados desde el ultimo update, ver skill `submodule-update`), no aplica espejar un solo commit — se usa una estructura propia, confirmada en el historial real (`higea` commit `343dd504`, Tarea 75512; `inversiones2050-homo` commit `c045d786`, Tarea 78242):

```
[UPD] <submodulo1>, <submodulo2>(, <submodulo3>): Actualizacion de submodulos

Tarea <numero>: <titulo de la tarea>

Se actualizaron los submodulos a los siguientes tags:

<submodulo1>: <tag1>
<submodulo2>: <tag2>
<submodulo3>: <tag3>

References:
- Ticket:
- Tarea: https://binaural.odoo.com/odoo/action-341/<numero>
- PR:
- Otros:
```

Reglas:
- **Tag**: `UPD` — no esta en la lista oficial del PDF corporativo (seccion 1), pero es el que el usuario ya usa en la practica para este caso (coincide con la nota de `branch-create` sobre el tipo de rama `upd`).
- **Modulos en la primera linea**: solo los submodulos que realmente cambiaron de tag en esa corrida, no todos los presentes en el proyecto.
- **Cuerpo**: un commit combinado por corrida (todos los submodulos actualizados juntos), listando cada uno con su tag nuevo — sin agregar tag anterior, rama de mantenimiento usada, ni un changelog embebido; por la naturaleza de estas actualizaciones periodicas esa informacion extra no hace falta en el commit.
- **References**: apunta a la Tarea de la actualizacion periodica en si (normalmente ya existe una Tarea para esto), no a un ticket de fix puntual.
- El PR resultante tampoco lleva seccion de "Test plan" (ver skill `pr-create`).
