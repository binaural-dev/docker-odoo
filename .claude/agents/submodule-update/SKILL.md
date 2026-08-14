---
name: submodule-update
description: Actualiza los submodulos (integra-addons, odoo-venezuela, third-party-addons) de un proyecto cliente a su ultimo tag de mantenimiento (beta), detectando automaticamente si el proyecto es Homologado u Operativo para elegir la rama correcta, y dejando el commit de bump siguiendo la convencion real ya usada en el historial. Usar cuando el usuario pida actualizar submodulos, subir de version integra-addons/odoo-venezuela/third-party-addons, o hacer el "update de submodulos" periodico de un proyecto.
---

# submodule-update

Automatiza el proceso que el usuario ya hace a mano: identificar el tipo de proyecto, encontrar el ultimo tag `-beta` de cada submodulo en la rama de mantenimiento correcta, traerlo sin perder cambios locales, y dejar el commit de bump con la misma estructura que ya usa en produccion (confirmada en `higea` e `inversiones2050-homo`).

Reutiliza, sin duplicar su logica: `project-type-detect` (Paso 1), `branch-create` (Paso 6), `commit-message` (Paso 7, ver su seccion "Caso especial: bump masivo"), `pr-create`/`git-flow` (Paso 9), y `extract_commits.py` de `reporte-incidencias-higea` (Paso 8).

## Informacion necesaria

1. **Proyecto objetivo** — *derivable*. Usar la misma resolucion de `project-type-detect` (Paso 1 de esa skill): si el cwd ya tiene `.gitmodules` propio, el proyecto es el cwd; si se corre desde la raiz de docker-odoo, es `src/custom/<nombre>` y hay que preguntar `<nombre>` si no es evidente. En el resto de este documento, `<proyecto>` se refiere a esa raiz ya resuelta (puede ser `.` o `src/custom/<nombre>`).
2. **Tarea de la actualizacion** (numero) — *preguntar siempre que no se haya mencionado*. Se usa en el nombre de la rama (Paso 6) y en las `References` del commit (Paso 7). Estas actualizaciones periodicas normalmente ya tienen una Tarea asignada en el modulo de proyectos.
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

### Paso 3 — Identificar el ultimo tag `-beta` por submodulo

Dentro de cada submodulo a actualizar:
```bash
cd <proyecto>/<submodulo>
git fetch origin --tags --force
git rev-parse HEAD                                    # puntero actual, guardar para el rango del Paso 8
git describe --tags --exact-match HEAD 2>/dev/null     # tag actual, si aplica

git tag --merged origin/<rama> --sort=-creatordate \
  | grep -E '^(l10nve_)?<version>\..*-beta\.[0-9]+$' | head -1
```
`--merged origin/<rama>` es importante: evita traer un tag de otra version/rama con nombre parecido.

Si no aparece ningun tag `-beta` (caso tipico de `third-party-addons`, que suele publicar tags planos sin sufijo de pre-release), usar el fallback:
```bash
git tag --merged origin/<rama> --sort=-creatordate \
  | grep -E '^(l10nve_)?<version>\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1
```

Repetir para cada submodulo a actualizar, guardando por cada uno: rama usada, tag/hash actual, tag propuesto.

### Paso 4 — Punto de control obligatorio (confirmacion)

Mostrar una tabla resumen antes de tocar nada:

| Submodulo | Rama de mantenimiento | Tag actual | Tag propuesto |
|---|---|---|---|
| integra-addons | l10nve_17.0 | l10nve_17.0.2.1.0-beta.5 | l10nve_17.0.2.2.0-beta.6 |
| odoo-venezuela | 17.0 | 17.0.2.0.5-beta.6 | 17.0.2.0.7-beta.8 |
| third-party-addons | 17.0 | 17.0.1.4.0 | 17.0.2.1.0 |

**Nunca continuar al Paso 5 sin aprobacion explicita del usuario.** Si el usuario pide excluir algun submodulo de esta tabla, quitarlo y seguir solo con los aprobados.

### Paso 5 — Traer el tag a cada submodulo SIN perder cambios locales

**Nunca hacer `git checkout <tag>`.** El cliente puede tener commits locales sobre el submodulo (parches puntuales de ese entorno) que un checkout directo del tag dejaria fuera de la vista o forzaria a descartar. Siempre traer el tag con un `pull`, que funde la historia local con la del tag en vez de reemplazarla:

```bash
cd <proyecto>/<submodulo>
git fetch origin --tags
git pull origin <tag_propuesto> --no-rebase
```

Esto funciona igual si el submodulo esta en una rama o en detached HEAD (el estado normal de un puntero de submodulo en este proyecto, ver `branch-create`): si hay commits locales, `--no-rebase` genera un merge que los conserva.

**Si el `pull` reporta conflictos, detenerse ahi y reportar al usuario** (que submodulo, que archivos en conflicto) — nunca resolver conflictos de merge de forma automatica o silenciosa. El usuario decide como resolverlos antes de continuar.

### Paso 6 — Crear la rama en el repo del cliente

Volver a la raiz del proyecto (`cd <proyecto>`) y aplicar `branch-create` tal cual:

- **origen**: la rama de staging real del proyecto (respetar el caso especial `mg_stg_*` si el proyecto esta en migracion de version, exactamente como ya lo detecta `branch-create` — `git branch -r | grep -i mg_stg`).
- **tipo**: `upd`.
- **tipo_asignacion**: `ta`.
- **id**: numero de la Tarea de la actualizacion (seccion "Informacion necesaria").
- **nombre**: `submodules_upd`.

Nombre final, reproduciendo el patron real ya visto en el historial (`mg_stg_l10n_ve_17.0_upd-ta_75512_submodules_upd`, `mg_stg_l10nve_17.0_upd-ta_78242_submodules_upd`):
```
<origen>_upd-ta_<id>_submodules_upd
```

Mostrar el nombre propuesto y confirmar antes de:
```bash
git fetch origin <rama_base>
git checkout -b <nombre_final> <rama_base>
```

### Paso 7 — Commit de bump combinado

Un solo commit para todos los submodulos actualizados en esta corrida. Reproducir tal cual la estructura real confirmada en el historial (`higea` commit `343dd504`, `inversiones2050-homo` commit `c045d786`) — ver tambien `commit-message`, seccion "Caso especial: bump masivo por actualizacion a tag de mantenimiento":

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

Mostrar el mensaje propuesto para aprobacion explicita antes de:
```bash
git add <submodulos_actualizados>
git commit
```

### Paso 8 — Informe rapido de cambios incluidos

Por cada submodulo actualizado, reutilizar el script ya existente de `reporte-incidencias-higea` (no duplicarlo):
```bash
python3 ~/.claude/agents/reporte-incidencias-higea/extract_commits.py \
  --repo <proyecto>/<submodulo> --range <sha_actual_del_paso_3>..<tag_propuesto> \
  --tags FIX,FEAT,HOTFIX,MIG
```
Presentar en el chat una tabla corta (submodulo, ticket, resumen) con lo que trajo cada bump — es feedback inmediato de la misma sesion, no requiere PDF ni criterio de redaccion extenso (eso lo hace el informe funcional del Paso 10).

### Paso 9 — Push + PR del repo del cliente

Seguir el flujo normal de `pr-create`/`git-flow`:
- Preguntar por separado si se hace push de la rama del Paso 6, y si se abre PR — nunca asumir aprobacion de un paso anterior.
- El PR va hacia la rama base usada como origen en el Paso 6 (la misma `staging`/`mg_stg_*` de donde partio).

### Paso 10 — Lanzar el informe funcional en background

Con los rangos `<sha_anterior>..<tag_propuesto>` ya calculados por submodulo en el Paso 3, invocar la skill `reporte-funcional-submodulos` via la tool `Agent` (`subagent_type: "reporte-funcional-submodulos"`), **en background** (sin bloquear el resto de la conversacion), pasandole en el prompt: proyecto, y por cada submodulo actualizado su ruta y su rango `<sha_anterior>..<tag_propuesto>` — para que no tenga que volver a derivarlos.

Avisar al usuario que el informe funcional quedara listo mas adelante y se entregara como PDF cuando termine. Esa misma skill, al terminar, archiva automaticamente cada incidencia en la biblioteca global (`~/.claude/agents/biblioteca-submodulos/SKILL.md`, cuyos datos viven fuera del repo en `~/binaural/biblioteca-submodulos/`) — no hace falta lanzar nada aparte para eso.

## Puntos de control (siempre pedir confirmacion explicita antes de)

- Paso 4: aprobar la tabla de tags propuestos, antes de tocar cualquier submodulo.
- Paso 5: si un `pull --no-rebase` reporta conflictos, detenerse y esperar decision del usuario.
- Paso 6: aprobar el nombre de la rama antes de crearla.
- Paso 7: aprobar el mensaje de commit antes de `git commit`.
- Paso 9: aprobar push y PR por separado (no se asume ninguno de los dos por defecto).

Estos puntos son independientes entre si — aprobar uno no aprueba los siguientes.
