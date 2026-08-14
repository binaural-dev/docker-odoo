---
name: reporte-incidencias-higea
description: Genera un reporte en PDF de incidencias (bugs) reportadas y resueltas en un repositorio, a partir de los commits [FIX]/[FEAT] de git log en un rango de fechas o de refs. Cada incidencia queda documentada en 4 campos (Resumen, Problema, Causa, Solucion) igual que el cuerpo de los commits del proyecto. Usar cuando el usuario pida un reporte de incidencias, reporte de bugs/hotfixes, un PDF de lo que se corrigio en un periodo, o quiera documentar/dejar constancia de los fixes resueltos en Higea (o cualquier otro repo custom) en un rango de tiempo o de commits.
---

# reporte-incidencias-higea

Genera un PDF con las incidencias resueltas en un repositorio, reconstruyendo para cada una los 4 campos que ya se usan en los commits/PRs de este proyecto: **Resumen, Problema, Causa, Solución**. Nace de reportes que se armaron a mano leyendo `git log` — esta skill automatiza la parte mecánica (extraer commits, armar el HTML, convertir a PDF) y deja la parte de criterio (decidir qué es una incidencia real y redactar los 4 campos) en manos de quien ejecuta la skill.

Archivos de esta skill:
- `extract_commits.py` — script que hace el `git log` y devuelve JSON. Puramente mecánico, no decide nada de contenido.
- `template.html` — plantilla con placeholders `{{...}}` para armar el reporte final.

## Restricción de datos (obligatoria)

Toda esta skill corre **en local**: el HTML y el PDF se generan y se entregan en el filesystem del usuario (`SendUserFile`), nunca se suben a un servicio externo. **No usar la tool `Artifact`** para este reporte ni ninguna otra herramienta que publique el contenido fuera de la máquina del usuario — los datos de la empresa/cliente no deben salir de la organización.

## Paso 1 — Determinar el alcance

Antes de ejecutar nada, se necesita:

1. **Rango**: fechas (`--since`/`--until`, ej. `2026-08-02` a `2026-08-03`) o un rango de refs (`--range abc123..def456`, útil si el usuario dice "desde el commit X" o "lo que entró en el PR Y"). **Si el usuario no dio ninguno de los dos, preguntar** — no asumir un periodo arbitrario, igual que no se asume autoría o contenido en las otras skills de este proyecto.
2. **Repositorio**: por default el directorio de trabajo actual si es un repo git; si el usuario menciona otro repo/submódulo (ej. "los fixes de odoo-venezuela"), usar `--repo <ruta>`.
3. **Rama o alcance**: por default la rama actualmente checked-out (`--branch`, sin especificar toma la actual). Si el usuario quiere solo lo que ya llegó a producción, usar `--branch release` (o la rama de producción del proyecto); si quiere ver todo lo resuelto sin importar si mergeó, usar `--all-branches`. Si no se especifica y el pedido es ambiguo entre "lo resuelto" (release) y "lo que se hizo" (rama de trabajo actual), preguntar.
4. **Tags a incluir**: por default `FIX,FEAT` (algunos fixes reales quedan taggeados `[FEAT]` cuando incluyen un módulo nuevo, ver Paso 3). Ampliar con `--tags` solo si el usuario lo pide explícitamente.

## Paso 2 — Extraer los commits

Ejecutar con la tool Bash:

```bash
python3 ~/.claude/agents/reporte-incidencias-higea/extract_commits.py \
  --repo <ruta_repo> \
  --since <YYYY-MM-DD> --until <YYYY-MM-DD> \
  --branch <rama>
```

o, con rango de refs:

```bash
python3 ~/.claude/agents/reporte-incidencias-higea/extract_commits.py \
  --repo <ruta_repo> --range <ref1>..<ref2>
```

La ruta del script es absoluta (`~/.claude/agents/...`), asi que funciona sin importar desde que directorio/proyecto se invoque la skill. El script ya excluye merges y filtra por tag; devuelve JSON con, por commit: `hash`, `date`, `author`, `subject`, `tag`, `module_guess`, `summary_guess`, `body` (cuerpo completo) y `references_guess` (Ticket/Tarea/PR/Otros ya parseados si existen).

Si devuelve `0 commits`, avisar al usuario y verificar rango/rama antes de seguir — no hay nada que reportar todavía, no inventar contenido.

## Paso 3 — Filtrar y redactar cada incidencia (el criterio es de quien ejecuta la skill, no del script)

El script trae **todo** lo que matchea el tag, incluyendo ruido que no es una incidencia real: bumps de versión de manifest, ajustes de lint/pre-commit, etc. Antes de incluir un commit en el reporte, preguntarse: *¿esto es algo que le costó tiempo/dinero a alguien porque algo no funcionaba, o es mantenimiento técnico interno?* Ejemplos ya vistos:
- Excluir: `[FIX] higea_pos: Elimina clave description obsoleta del manifest` (solo pasa un check de lint), `[FIX] higea_pos: Incrementa version de manifest` (bump sin fix asociado).
- Incluir aunque diga `[FEAT]`: si el cuerpo describe un bug real corregido (ej. "Corrige obligatoriedad de contacto en traslados"), es una incidencia aunque el commit se haya taggeado como feature por crear un módulo nuevo en el proceso.

**Fusionar commits que son la misma incidencia**: si un commit posterior corrige un efecto secundario o regresión introducida por un fix anterior sobre el mismo problema (el cuerpo suele decirlo explícito: "efecto secundario del fix anterior", "al revés", referencia al hash del commit original), **no** listarlos como dos incidencias separadas — son la misma incidencia todavía no resuelta del todo. Unificarlos en un solo bloque: un título que cubra ambas caras del problema, un `Resumen`/`Problema` que narre las dos etapas en orden cronológico, una `Causa` que explique tanto el bug original como por qué la primera corrección no fue suficiente, una `Solución` que describa el estado final, y en `meta` listar todos los commits involucrados (`Commits: hash1, hash2`) en vez de uno solo.

Ante la duda de si un commit es o no una incidencia real, **preguntar al usuario** en vez de decidir en silencio — igual que con los tickets dudosos de `reporte-horas-ia`.

Para cada commit que sí queda, redactar (en español, en prosa clara, sin copiar literalmente el cuerpo del commit si se puede sintetizar mejor):

| Campo | De dónde sale |
|---|---|
| **Resumen** | Una frase: qué le pasaba al usuario/sistema. Si el `subject` ya lo dice bien, se puede reusar casi tal cual. |
| **Problema** | El síntoma observable (qué fallaba, para quién, en qué pantalla/flujo). |
| **Causa** | La causa raíz técnica. Si el cuerpo del commit ya la explica (busca en general el porqué, con palabras como "porque", "debido a", "ya que"), reusarla; si el cuerpo es escueto, sintetizar a partir del `diff` (`git show <hash>`) si hace falta más contexto. |
| **Solución** | Qué se cambió concretamente para resolverlo. |
| **Ticket** | `references_guess.Ticket` si existe y no es un placeholder vacío; si dice algo como "(hotfix sin ticket)" o viene vacío, mostrar "Hotfix sin ticket". Si hay número de ticket, armar el link `https://binaural.odoo.com/odoo/my-tickets/<numero>` (usar el dominio que corresponda al cliente si no es Higea/Binaural). |
| **Módulo** | `module_guess` es una aproximación (regex sobre el subject) — verificar contra el subject completo, especialmente en commits con varios módulos separados por coma o con formato irregular (ej. `[FIX](modulo)` sin dos puntos). **Si el subject usa el nombre de un submódulo** (ej. `[FIX] odoo-venezuela: ...`, `[FIX] integra-addons: ...`), ese es el repo contenedor, no el módulo de Odoo real que cambió — leer el cuerpo del commit para encontrar el nombre del addon concreto (suele aparecer explícito, ej. "en `order_model.js` (modulo l10n_ve_pos)"); si el cuerpo no lo aclara, revisar el diff con `git show <hash>` para ver la carpeta del módulo tocado. |

No es necesario un paso intermedio de JSON: se puede ir directo de los datos crudos del Paso 2 a las cadenas HTML del Paso 4.

## Paso 4 — Armar el HTML

Leer `~/.claude/agents/reporte-incidencias-higea/template.html` con la tool Read y reemplazar los placeholders:

```
{{TITULO}}               → ej. "Reporte de Incidencias Resueltas — Higea"
{{PERIODO}}               → ej. "2026-08-02 al 2026-08-03" (o "commit abc123 a def456")
{{FECHA_GENERACION}}       → fecha de hoy
{{FUENTE}}                 → ej. "historial de commits del repositorio custom/higea, rama stg_..."
{{FILAS_RESUMEN}}          → un <tr> por incidencia en la tabla resumen
{{INCIDENCIAS_DETALLE}}    → un bloque <div class="incident"> por incidencia
{{NOTA_PIE}}               → nota de uso interno + qué se excluyó y por qué (transparencia de alcance)
```

**Fila de la tabla resumen:**
```html
<tr>
  <td>{{N}}</td><td>{{FECHA}}</td><td><code>{{MODULO}}</code></td><td>{{RESUMEN}}</td><td>{{TICKET}}</td>
</tr>
```

**Bloque de detalle por incidencia:**
```html
<div class="incident">
  <h2>{{N}}. {{TITULO_INCIDENCIA}}</h2>
  <div class="meta"><span>Módulo: {{MODULO}}</span><span>Fecha: {{FECHA}}</span><span>Commit: {{HASH}}</span></div>
  <div class="field"><span class="label">Resumen:</span> {{RESUMEN}}</div>
  <div class="field"><span class="label">Problema:</span> {{PROBLEMA}}</div>
  <div class="field"><span class="label">Causa:</span> {{CAUSA}}</div>
  <div class="field"><span class="label">Solución:</span> {{SOLUCION}}</div>
</div>
```

Guardar el HTML con la tool Write en el directorio scratchpad de la sesión (no en el repo del proyecto — es un artefacto temporal de generación, no código fuente).

## Paso 5 — Convertir a PDF

```bash
weasyprint <ruta_scratchpad>/reporte_incidencias_<slug>.html <ruta_scratchpad>/reporte_incidencias_<slug>.pdf
```

`weasyprint` ya está disponible en este entorno (no requiere instalación). Si el comando falla porque no está instalado, avisar al usuario en vez de intentar instalarlo sin permiso (instalar paquetes es una acción que requiere confirmación).

## Paso 6 — Entregar

Entregar el PDF con `SendUserFile` (nunca con `Artifact` — ver restricción de datos arriba). Mencionar en el mensaje cuántas incidencias quedaron y si se excluyó algo relevante del rango original (ej. "se excluyeron 2 commits que eran ajustes técnicos sin incidencia asociada").

## Reglas importantes

1. **El script no decide contenido**: `extract_commits.py` solo hace `git log` + parseo mecánico del subject/references. Toda síntesis de Resumen/Problema/Causa/Solución y todo filtrado de qué es o no una incidencia real es responsabilidad de quien ejecuta la skill.
2. **Nunca inventar una incidencia ni un ticket**: si el cuerpo del commit no alcanza para llenar un campo con confianza, decirlo explícitamente en el reporte (ej. "Causa no documentada en el commit") en vez de rellenar con texto genérico.
3. **Preguntar ante la duda** sobre rango, rama, o si un commit dudoso (`[FEAT]` que parece fix, o viceversa) debe incluirse — no decidir en silencio.
4. **Nunca subir el HTML/PDF a un servicio externo** (sin `Artifact`, sin publicar): el reporte se queda en el filesystem local y se entrega solo con `SendUserFile`.
5. **Guardar el PDF final en el directorio scratchpad de la sesión**, no dentro del repositorio del proyecto.
6. **Fondo blanco explícito**: `template.html` ya declara `background: #ffffff` en `html`, `body` y `@page` — no quitarlo. Sin eso, algunos visores de PDF con modo oscuro invierten la página (fondo oscuro, texto que sigue oscuro) porque no detectan un fondo "real"; declararlo explícito evita que dependa del visor de quien lo abre.
