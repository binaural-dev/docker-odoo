---
name: submodule-update
description: Actualiza los submodulos (integra-addons, odoo-venezuela, third-party-addons) de un proyecto cliente a un tag de mantenimiento reciente (beta o alpha, a eleccion del usuario), detectando automaticamente si el proyecto es Homologado u Operativo para elegir la rama correcta, y dejando el commit de bump siguiendo la convencion real ya usada en el historial. Usar cuando el usuario pida actualizar submodulos, subir de version integra-addons/odoo-venezuela/third-party-addons, o hacer el "update de submodulos" periodico de un proyecto.
---

# submodule-update

Automatiza el proceso que el usuario ya hace a mano: identificar el tipo de proyecto, encontrar los ultimos tags `-beta` y `-alpha` de cada submodulo en la rama de mantenimiento correcta, dejar que el usuario elija cual de los dos (u otro) aplica, traerlo sin perder cambios locales, y dejar el commit de bump con la misma estructura que ya usa en produccion (confirmada en `higea` e `inversiones2050-homo`).

Reutiliza, sin duplicar su logica: `project-type-detect` (Paso 1), `branch-create` (Paso 6), `commit-message` (Paso 7, ver su seccion "Caso especial: bump masivo"), `pr-create`/`git-flow` (Paso 9).

## Informacion necesaria

1. **Proyecto objetivo** — *derivable*. Usar la misma resolucion de `project-type-detect` (Paso 1 de esa skill): si el cwd ya tiene `.gitmodules` propio, el proyecto es el cwd; si se corre desde la raiz de docker-odoo, es `src/custom/<nombre>` y hay que preguntar `<nombre>` si no es evidente. En el resto de este documento, `<proyecto>` se refiere a esa raiz ya resuelta (puede ser `.` o `src/custom/<nombre>`).
2. **Tarea o Ticket de la actualizacion** (tipo + numero) — *preguntar siempre que no se haya mencionado, sin asumir cual de los dos aplica*. Se usa en el nombre de la rama (Paso 6, como `tipo_asignacion` de `branch-create`: `ta` para Tarea, `ti` para Ticket) y en las `References` del commit (Paso 7). Estas actualizaciones periodicas normalmente ya tienen una Tarea asignada en el modulo de proyectos, pero no siempre — a veces la actualizacion de submodulos es en si misma la solucion de un Ticket puntual de un cliente (ej. un fix que el cliente reporto y que ya esta mergeado en la rama de mantenimiento, y la actualizacion del submodulo es lo unico que hace falta para llevarselo). En ese caso usar `ti` + el numero de Ticket, no inventar una Tarea.
3. **Submodulos a actualizar** — *derivable* via `project-type-detect`, pero confirmar con el usuario si quiere actualizar todos los presentes o solo algunos en particular.

## Flujo de trabajo

### Paso 1 — Detectar proyecto y tipo

Aplicar `project-type-detect`: tipo (Homologado/Operativo), `odoo_version`, submodulos presentes. Ver ese skill para el detalle de deteccion via `.gitmodules`.

### Paso 2 — Determinar la rama de mantenimiento por submodulo

- **`integra-addons`**: `l10nve_<version>` si el proyecto es Homologado, `<version>` si es Operativo — es el unico submodulo con dos lineas de mantenimiento paralelas por version de Odoo. Verificar que la rama exista en remoto:
  ```bash
  git -C <proyecto>/integra-addons ls-remote --heads origin <rama>
  ```
  Si `l10nve_<version>` no existe todavia para esa version (ej. una homologacion de una version nueva de Odoo aun no publicada), **detenerse y preguntar** al usuario en vez de caer a la rama operativa por defecto.
- **`odoo-venezuela`** (si el proyecto es Homologado): `<version>`, sin prefijo `l10nve_` — el repo entero ya es la capa homologada.
- **`third-party-addons`**: `<version>` siempre, sin distincion por tipo de proyecto.

### Paso 3 — Identificar los candidatos de tag por submodulo (`-beta` Y `-alpha`)

> **Por que se buscan los dos candidatos y no solo `-beta`:** hasta esta version el skill asumia sin mas que el ultimo `-beta` era la opcion correcta y la proponia directo en el Paso 4. El 2026-08-18, durante la migracion de version de `bodegonactual` (16→17), se detecto que en `integra-addons` rama `17.0` el ultimo `-beta` (`17.0.2.1.1-beta.6`, del 22 de julio) tenia casi un mes de atraso frente al desarrollo real, que siguio publicandose solo bajo tags `-alpha` hasta `17.0.3.4.0-alpha.9` (16 de agosto, coincidiendo exactamente con la punta de la rama). El skill nunca llego a mostrar el `-alpha` como opcion; el usuario se entero por fuera del flujo y en ese caso prefirio el `-alpha` por tener mas fixes. Por eso ahora se buscan y muestran ambos candidatos con su fecha, y es el usuario quien decide cual usar (ver Paso 4).

Dentro de cada submodulo a actualizar:
```bash
cd <proyecto>/<submodulo>
git fetch origin --tags --force
git rev-parse HEAD                                    # puntero actual
git describe --tags --exact-match HEAD 2>/dev/null     # tag actual, si aplica

# Candidatos alpha: ultimos 5
git tag --merged origin/<rama> --sort=-creatordate \
  | grep -E '^(l10nve_)?<version>\..*-alpha\.[0-9]+$' | head -5

# Candidatos beta: ultimos 3
git tag --merged origin/<rama> --sort=-creatordate \
  | grep -E '^(l10nve_)?<version>\..*-beta\.[0-9]+$' | head -3
```
`--merged origin/<rama>` es importante: evita traer un tag de otra version/rama con nombre parecido.

Se piden mas alpha que beta (5 vs 3) porque en la practica el alpha es la linea que se publica con mas frecuencia — reduce el riesgo de que la ventana de 5 quede corta y no llegue a cubrir varios dias de desarrollo real. No es una regla rigida: si el usuario pide ver mas candidatos de cualquiera de los dos tipos, ampliar la busqueda sin problema.

Para cada candidato encontrado (los hasta 5 alpha y hasta 3 beta), obtener su fecha de creacion — es lo que permite notar una brecha temporal grande entre ambos, o identificar cual trae mas fixes recientes, como paso en el caso real:
```bash
git log -1 --format='%ci' <tag>
```

Si no aparece ningun tag `-beta` NI `-alpha` (caso tipico de `third-party-addons`, que suele publicar tags planos sin sufijo de pre-release), usar el fallback de siempre — este caso no cambia:
```bash
git tag --merged origin/<rama> --sort=-creatordate \
  | grep -E '^(l10nve_)?<version>\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1
```

Repetir para cada submodulo a actualizar, guardando por cada uno: rama usada, tag/hash actual, candidato `-beta` con fecha, candidato `-alpha` con fecha, y el tag de fallback si no hubo ni beta ni alpha.

### Paso 4 — Punto de control obligatorio (confirmacion)

Mostrar, antes de tocar nada, una tabla por submodulo con **hasta 5 candidatos `-alpha` y hasta 3 `-beta`** (los del Paso 3), ordenados por fecha descendente, marcando el tag actual como referencia — nunca colapsar la lista a un solo candidato por tipo ni proponer directo uno solo como si fuera la respuesta obvia:

**integra-addons** — rama `17.0`, tag actual `17.0.2.1.0-beta.5`

| Tipo | Tag | Fecha |
|---|---|---|
| alpha | 17.0.3.4.0-alpha.9 | 2026-08-16 |
| alpha | 17.0.3.3.2-alpha.8 | 2026-08-14 |
| alpha | 17.0.3.3.1-alpha.7 | 2026-08-13 |
| alpha | 17.0.3.3.0-alpha.6 | 2026-08-12 |
| alpha | 17.0.3.2.0-alpha.5 | 2026-08-08 |
| beta | 17.0.2.1.1-beta.6 | 2026-07-22 |
| beta | 17.0.2.1.0-beta.5 | 2026-07-15 |
| beta | 17.0.2.0.9-beta.4 | 2026-07-09 |

**odoo-venezuela** — rama `17.0`, tag actual `17.0.2.0.5-beta.6`

| Tipo | Tag | Fecha |
|---|---|---|
| alpha | 17.0.2.0.9-alpha.2 | 2026-08-11 |
| alpha | 17.0.2.0.8-alpha.1 | 2026-08-10 |
| beta | 17.0.2.0.7-beta.8 | 2026-08-10 |
| beta | 17.0.2.0.6-beta.7 | 2026-08-03 |

**third-party-addons** — rama `17.0`, tag actual `17.0.1.4.0`

(no publica `-beta` ni `-alpha`) → fallback: `17.0.2.1.0`

Si hay una brecha de fechas grande entre el `-beta` mas reciente y el `-alpha` mas reciente (como en el ejemplo de `integra-addons` arriba, tomado del caso real detectado en `bodegonactual`), señalarla explicitamente al mostrar la tabla — es la señal de que el `-alpha` puede traer fixes relevantes que el `-beta` todavia no tiene.

Preguntar explicitamente al usuario, por cada submodulo, **cual candidato puntual de la lista aplica para esta corrida** (no necesariamente el mas reciente de cada tipo — el usuario puede preferir un alpha o beta mas viejo de la lista, o un tag fuera de ella) — nunca asumir el primero de la lista por default.

**Nunca continuar al Paso 5 sin que el usuario haya elegido explicitamente un tag puntual por submodulo.** Si el usuario pide excluir algun submodulo de esta tabla, quitarlo y seguir solo con los aprobados.

### Paso 5 — Traer el tag a cada submodulo SIN perder cambios locales

**Nunca hacer `git checkout <tag>`.** El cliente puede tener commits locales sobre el submodulo (parches puntuales de ese entorno) que un checkout directo del tag dejaria fuera de la vista o forzaria a descartar. Siempre traer el tag con un `pull`, que funde la historia local con la del tag en vez de reemplazarla:

```bash
cd <proyecto>/<submodulo>
git fetch origin --tags
git pull origin <tag_propuesto> --no-rebase
```

Esto funciona igual si el submodulo esta en una rama o en detached HEAD (el estado normal de un puntero de submodulo en este proyecto, ver `branch-create`): si hay commits locales, `--no-rebase` genera un merge que los conserva.

**Si el `pull` reporta conflictos, detenerse ahi y reportar al usuario** (que submodulo, que archivos en conflicto) — nunca resolver conflictos de merge de forma automatica o silenciosa. El usuario decide como resolverlos antes de continuar.

### Paso 5.5 — Publicar el merge del submodulo en su propio remoto (si no fue fast-forward)

> **Por que este paso existe:** detectado el 2026-08-18 durante la actualizacion de `inversiones2050-homo` (Ticket 14651). El `pull --no-rebase` del Paso 5 corre casi siempre sobre un submodulo en detached HEAD; si el puntero local no era ancestro directo del tag (por ejemplo, porque el cliente tenia un fix propio encima, como el commit de Ticket 14366 en `odoo-venezuela`), git genera un merge commit real — y ese commit **solo existe en este clon local**, no en ningun remoto. Si se comitea el bump del Paso 7 apuntando a ese commit sin publicarlo antes, cualquier otro clon (CI, otro dev, otro ambiente) fallara al hacer `git submodule update` porque el objeto no existe en `origin`.

Para cada submodulo actualizado en el Paso 5, verificar si el commit resultante ya es alcanzable desde algun remote-tracking branch:

```bash
cd <proyecto>/<submodulo>
git branch -r --contains $(git rev-parse HEAD)
```

- Si aparece al menos una rama remota (caso tipico de fast-forward, ej. `third-party-addons`), no hace falta hacer nada — el commit ya esta publicado.
- Si no aparece ninguna (el `pull` genero un merge real), publicarlo en una rama dedicada del remoto del submodulo, siguiendo el patron real ya usado en el historial (`origin/9ce1f1da_fix-ti_14366_iva_retention_payment_context` en `odoo-venezuela`, `origin/05553a53_upd-ta_78242_submodules_upd` en `integra-addons`):

  ```
  <hash_corto_del_puntero_previo_al_pull>_<sufijo_de_la_rama_del_Paso_6_sin_el_origen>
  ```

  Ejemplo: si el puntero previo era `4441f37b...` y la rama del Paso 6 sera `mg_stg_l10nve_17.0_upd-ti_14651_submodules_upd`, el nombre queda `4441f37b_upd-ti_14651_submodules_upd`.

  ```bash
  git push origin HEAD:refs/heads/<nombre_de_rama>
  ```

  Verificar despues que quedo publicado:
  ```bash
  git branch -r --contains $(git rev-parse HEAD)
  ```

**Punto de control:** mostrar el nombre de rama propuesto por submodulo y pedir confirmacion explicita antes de este `push` — es una accion visible en un repo compartido (`integra-addons`/`odoo-venezuela`/`third-party-addons`), igual de sensible que el push del Paso 9. Este paso debe quedar resuelto **antes** de comitear el bump del Paso 7, para que el commit del repo cliente nunca apunte a un objeto de submodulo huerfano.

### Paso 6 — Crear la rama en el repo del cliente

Volver a la raiz del proyecto (`cd <proyecto>`) y aplicar `branch-create` tal cual:

- **origen**: la rama de staging real del proyecto (respetar el caso especial `mg_stg_*` si el proyecto esta en migracion de version, exactamente como ya lo detecta `branch-create` — `git branch -r | grep -i mg_stg`).
- **tipo**: `upd`.
- **tipo_asignacion**: `ta` o `ti`, segun lo que se haya confirmado en "Informacion necesaria" (Tarea o Ticket) — no asumir `ta` por default.
- **id**: numero de la Tarea o Ticket correspondiente.
- **nombre**: `submodules_upd`.

Nombre final, reproduciendo el patron real ya visto en el historial para el caso Tarea (`mg_stg_l10n_ve_17.0_upd-ta_75512_submodules_upd`, `mg_stg_l10nve_17.0_upd-ta_78242_submodules_upd`) — mismo patron con `ti` cuando la actualizacion resuelve un Ticket puntual:
```
<origen>_upd-<tipo_asignacion>_<id>_submodules_upd
```

Mostrar el nombre propuesto y confirmar antes de:
```bash
git fetch origin <rama_base>
git checkout -b <nombre_final> <rama_base>
```

### Paso 7 — Commit de bump combinado

Un solo commit para todos los submodulos actualizados en esta corrida. Reproducir tal cual la estructura real confirmada en el historial (`higea` commit `343dd504`, `inversiones2050-homo` commit `c045d786`) — ver tambien `commit-message`, seccion "Caso especial: bump masivo por actualizacion a tag de mantenimiento":

Caso Tarea:
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

Caso Ticket (la actualizacion de submodulos es en si misma la solucion del ticket, ej. un fix del cliente que ya esta mergeado en la rama de mantenimiento y solo falta llevarselo):
```
[UPD] <submodulo1>, <submodulo2>(, <submodulo3>): Actualizacion de submodulos

Ticket <numero>: <titulo del ticket>

Se actualizaron los submodulos a los siguientes tags:

<submodulo1>: <tag1>
<submodulo2>: <tag2>
<submodulo3>: <tag3>

References:
- Ticket: https://binaural.odoo.com/odoo/my-tickets/<numero>
- Tarea:
- PR:
- Otros:
```

Mostrar el mensaje propuesto para aprobacion explicita antes de:
```bash
git add <submodulos_actualizados>
git commit
```

### Paso 8 — Validacion manual opcional (a criterio del usuario)

Este bump solo trae commits ya integrados y probados en la rama de mantenimiento compartida (`l10nve_<version>`/`<version>`) — no es codigo nuevo sin validar, por lo que correr `./odoo update`/tests aqui no es un paso obligatorio de esta skill (a diferencia de un PR con codigo nuevo, ver `pr-create`). Si el usuario quiere verificar igual que el proyecto sigue actualizando bien con los submodulos nuevos, puede ejecutarlo el mismo, cuando quiera, con:
```bash
./odoo update <instancia> -d <db> -m <modulos_dependientes>
```
Esta skill no lo ejecuta ni lo pide como parte del flujo — sigue directo del Paso 7 (commit de bump) al Paso 9 (push + PR).

### Paso 9 — Push + PR del repo del cliente

Seguir el flujo normal de `pr-create`/`git-flow`:
- Preguntar por separado si se hace push de la rama del Paso 6, y si se abre PR — nunca asumir aprobacion de un paso anterior.
- El PR va hacia la rama base usada como origen en el Paso 6 (la misma `staging`/`mg_stg_*` de donde partio).

## Puntos de control (siempre pedir confirmacion explicita antes de)

- Paso 4: el usuario debe elegir explicitamente, por submodulo, entre el candidato `-beta` y el `-alpha` (u otro tag) antes de tocar cualquier submodulo — nunca asumir `-beta` por default.
- Paso 5: si un `pull --no-rebase` reporta conflictos, detenerse y esperar decision del usuario.
- Paso 5.5: si el merge no fue fast-forward, aprobar el nombre de la rama del submodulo antes de publicarla en su remoto — este paso va antes del commit del Paso 7, nunca despues.
- Paso 6: aprobar el nombre de la rama antes de crearla.
- Paso 7: aprobar el mensaje de commit antes de `git commit`.
- Paso 9: aprobar push y PR por separado (no se asume ninguno de los dos por defecto).

Estos puntos son independientes entre si — aprobar uno no aprueba los siguientes.
