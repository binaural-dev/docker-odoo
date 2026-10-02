---
name: reporte-horas-ia
description: Genera reportes de horas con estimacion de productividad con/sin IA a partir de una hoja de horas PDF y los commits en repositorios custom. Analiza tickets TI/TA, revisiones de PR e incidencias/migraciones sin numero de ticket, cruza con git log para verificar autoria, y produce un HTML con columnas: Nro TI/TA, Titulo, Descripcion, Con IA, Mayor impacto sin IA, Sin IA. Usar cuando el usuario pida generar informe de horas, reporte de horas, o analizar hoja de horas con commits.
---

# reporte-horas-ia

Genera un reporte HTML de horas trabajadas con estimacion de productividad con y sin asistencia de IA, a partir de:
1. Una hoja de horas en PDF (extraida con `pdftotext -layout`)
2. Commits en los repositorios `src/custom/*/` y sus submodulos

La plantilla HTML se encuentra en `.claude/skills/reporte-horas-ia/template.html` dentro del repositorio docker-odoo.

## Flujo de trabajo

### Paso 1: Extraer la hoja de horas

Ejecutar con la tool Bash:
```bash
pdftotext -layout "ruta/al/archivo.pdf" -
```

Del texto extraido, identificar:
- **Periodo**: extraer del nombre del archivo o del contenido (ej: "15 al 30 de junio de 2026")
- **Empleado**: extraer del contenido
- **Actividades**: cada fila con fecha, tarea, descripcion y tiempo

### Paso 2: Identificar unidades de trabajo (con ticket y sin ticket)

**a) Tickets TI/TA**: buscar todos los numeros de ticket/tarea mencionados en la hoja con regex:

```
(?:TI|TA)[_\s#-]*(\d{4,6})
```

Extraer tambien las horas asociadas a cada ticket y la descripcion de la hoja.

**b) Bloques de trabajo sin ticket**: no descartar automaticamente las filas de la hoja de horas que no traen numero TI/TA. Revisarlas — suelen ser trabajo real y trazable en git, solo que la hoja no le puso numero:

- **Incidencias sin ticket**: filas con encabezado `INCIDENCIAS / <titulo>` (ej. "Realizar ajuste en reporte de Libro de Ventas...", "Corregir Error de validacion por stock insuficiente en traslado", "Verificar inconsistencia en monto alterno..."). Agrupar todas las filas que compartan el mismo `<titulo>` (aunque esten en fechas distintas) como una sola unidad de trabajo, sumando sus horas.
- **Migraciones tecnicas de modulos custom**: filas con encabezado tipo `Migración <Cliente> / Migración Técnica de Módulos Custom (vX a vY)` — es trabajo real de migracion (no un bug puntual), tratarlo como una unidad de trabajo propia agrupada por cliente+encabezado, no como "sin evidencia".
- **Trabajo mencionado en la descripcion sin encabezado propio** (ej. "Revision del caso de asientos desbalanceados y su PR a odoo-venezuela" dentro de una fila de "Post Migración HIGEA"): si la descripcion nombra un tema tecnico concreto y distinto del resto de filas del mismo encabezado, puede tratarse como sub-unidad propia si tiene commits identificables por palabra clave (paso 3b).

Para cada bloque sin ticket, definir un titulo corto en base al texto de la hoja (ej. "Ajuste Reporte Z / Libro de Ventas", "Error de stock insuficiente en traslado", "Asientos desbalanceados HIGEA") — este titulo se usa provisionalmente como `{{TITULO_TICKET}}`, pero el Paso 3c casi siempre revela el numero de ticket real, que debe reemplazarlo.

### Paso 3: Buscar evidencia (commits, PRs revisados, y el ticket real en Odoo)

**REGLA DE ORO: buscar en TODOS los repos bajo `src/custom/` (y sus submodulos), nunca solo en el/los repo(s) del cliente que "suena" en la fila de la hoja.** La hoja de horas no agrupa por cliente de forma confiable — una fila bajo el encabezado de un cliente puede corresponder al repo de otro cliente completamente distinto (ej. una incidencia listada junto a filas de "Higea" resulto pertenecer al repo `bisuteria888`). Saltarse repos por asumir el cliente es la causa mas comun de tickets/bloques que parecen "sin evidencia" y no lo estan.

**a) Por numero de ticket (git log)**: para cada ticket encontrado, buscar commits en TODOS los repositorios bajo `src/custom/` Y sus submodulos (`integra-addons/`, `odoo-venezuela/`, `third-party-addons/`) — ver comando abajo.

**b) Por palabra clave (bloques sin ticket, git log)**: para cada bloque identificado en el Paso 2b, extraer 2-3 palabras clave del titulo (ej. "Libro de Ventas" → `libro.*venta\|reporte.*z\|secuencia`, "stock insuficiente" → `stock.*insuficiente\|traslado`, "monto alterno" → `alterno\|igtf`, "asientos desbalanceados" → `desbalanceado\|unbalanced`) y buscarlas en los mensajes de commit, **en todos los repos y sus submodulos**, dentro del rango de fechas del bloque:

```bash
git -C "<repo>" log --all --since="<fecha_inicio>" --until="<fecha_fin>" \
  --format="%h|%ad|%an|%ae|%s" --date=short -i --grep="<palabra_clave>"
```

Si el titulo en español no da resultado, probar tambien el equivalente en ingles usado en nombres de modulo/commit (`unbalanced`, `stock`, `alternate`, etc). Revisar tambien el **cuerpo completo del commit** (`git log <hash> -1 --format="%s%n%b"`), no solo el asunto: el numero de ticket real suele estar citado ahi (`Ticket: https://binaural.odoo.com/odoo/my-tickets/NNNNN`) aunque la hoja de horas no lo haya escrito. No asumir que "sin ticket en la hoja" significa "sin commit" ni "sin numero real" — revisar primero.

**c) Revisiones de PR sin commit propio (GitHub, no aparece en git log)**: cuando `git log` no muestra nada para un ticket/bloque, no asumir que no hay evidencia — los comentarios de revision de PR (approve, request changes) no dejan commit y por tanto son invisibles para git. Usar `gh` (ya autenticado) para buscarlos:

```bash
gh api graphql -f query='
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    pullRequests(first:100, states:[MERGED,OPEN,CLOSED], orderBy:{field:UPDATED_AT, direction:DESC}) {
      nodes { number title reviews(first:10) { nodes { author { login } submittedAt state } } }
    }
  }
}' -f owner=binaural-dev -f name="<repo-en-github>" \
  --jq '.data.repository.pullRequests.nodes[] as $pr | $pr.reviews.nodes[] | select(.author.login=="<usuario-github-del-empleado>" and .submittedAt >= "<inicio-periodo>" and .submittedAt <= "<fin-periodo>") | "\(.submittedAt)|#\($pr.number)|\(.state)|\($pr.title)"'
```

El nombre del repo en GitHub puede diferir del directorio local (ej. el directorio `countryclub-17.0` corresponde al repo `countryclub` en GitHub) — obtenerlo con `git -C "<repo>" remote get-url origin`. Repetir para cada repo custom. Cruzar la fecha/hora de cada review contra las horas de la hoja: coincide con precision de minutos cuando es el mismo evento. `gh pr view <numero> --repo <owner>/<repo> --json title,mergedAt,author,reviews` da el detalle completo de una revision puntual, incluido el cuerpo del comentario (util para juzgar la profundidad real de la revision al clasificar complejidad en el Paso 5).

Si en el rango de fechas solo aparecen commits `Merge pull request #...` del autor pero el codigo lo escribio otra persona (verificar con `%an` del commit no-merge), o una revision de GitHub sin commit propio, clasificar esa fila como **Revision de PR** (ver Paso 4) en vez de descartarla.

**d) Buscar el ticket/tarea real en el Odoo central (cuando a y b/c no alcanzan, o para confirmar el numero)**: si hay un conector MCP de solo lectura al Odoo central de Binaural disponible en la sesion, buscar por **el texto exacto del titulo de la fila de la hoja** — la hoja de horas frecuentemente copia el titulo completo del ticket/tarea tal cual, sin el prefijo `TI#`/`TA#`. Esto resuelve casi cualquier bloque "sin ticket":

- Probar primero `helpdesk.ticket` (incidencias/bugs, prefijo `TI`) con dominio `[["name", "ilike", "<fragmento del titulo>"]]`, o acotado por `user_id.name` + rango de `create_date` si el titulo es muy generico.
- **Si no aparece ahi, probar tambien `project.task`** (tareas de proyecto — features, migraciones, trabajo planificado; prefijo `TA`) con el mismo patron de busqueda por `name ilike` y `user_ids in [<id_empleado>]`. Un bloque que "suena a proyecto grande" (ej. una migracion tecnica completa) es tan probable que sea un `project.task` como que no tenga ticket — no asumir que las migraciones/tareas de alcance amplio nunca tienen numero. El `id` del registro es el numero de referencia (`TA #<id>`), no hay que inventar ni pedir un campo de codigo aparte.
- Leer el registro completo (`get_record` con `description`, `github_pr_ids` en helpdesk.ticket) — la descripcion del bug/tarea suele confirmar si es el mismo caso, y `github_pr_ids` enlaza a los PRs reales (consultar `github.pr` por esos ids para obtener `owner/repo/pull/numero`, y de ahi `gh pr view` para fecha/autor/estado).
- Un ticket/tarea puede tener varios PRs en repos distintos para el mismo caso (ej. el fix en el repo del cliente + el fix upstream en `odoo-venezuela`/`integra-addons`) — sumarlos todos a esa misma fila, no crear filas duplicadas.
- Un ticket sin ningun PR vinculado y en una etapa como "Validacion" suele significar que se resolvio con un ajuste de datos/configuracion, no de codigo — es evidencia legitima igual, se documenta esa naturaleza en la `{{DESCRIPCION}}`.

Solo dejar `S/T` (sin ticket) cuando la busqueda en `helpdesk.ticket` Y `project.task` no encontro nada razonable — no por default en cualquier bloque que llegue sin numero desde la hoja. Si no hay conector MCP a Odoo disponible en la sesion, dejarlo como pendiente y preguntar al usuario en el Paso 6 en vez de asumir que no existe ticket/tarea.

**Repositorios custom** (buscar con Bash):
```bash
for repo in src/custom/*/; do
  if [ -d "$repo/.git" ] || [ -f "$repo/.git" ]; then
    # buscar aqui
  fi
done
```

**Submodulos** (dentro de cada repo custom, si existen):
- `integra-addons/`
- `odoo-venezuela/`
- `third-party-addons/`

**Busqueda de commits** por ticket y periodo:
```bash
git -C "<repo>" log --all --since="<fecha_inicio>" --until="<fecha_fin>" \
  --format="%h %ad %an <%ae> %s" --date=short --grep="<numero_ticket>"
```

Para tickets no encontrados, buscar tambien en ramas locales con:
```bash
git -C "<repo>" branch -a | grep -i "<numero_ticket>"
```

### Paso 4: Cruzar tickets con commits y verificar autoria

Para cada ticket o bloque sin ticket, determinar:

| Estado | Criterio | Accion |
|---|---|---|
| **Desarrollo propio** | Commit del autor del informe + mensaje contiene el numero de ticket (o la palabra clave, si es bloque sin ticket) | Incluir en el reporte |
| **Revision de PR** | El autor del informe solo aparece en commits `Merge pull request`, y el codigo (commits no-merge) es de otro autor; la hoja de horas describe explicitamente "revision de PR" o similar | Incluir en el reporte como categoria propia (no es "sin evidencia": el merge commit y el PR revisado son la evidencia) |
| **Otro autor sin revision explicita** | Commit existe pero el autor NO es el del informe, y la hoja no describe una revision/merge hecha por el | Excluir del reporte |
| **Sin commits** | No se encontro ningun commit ni merge en el periodo, ni por ticket ni por palabra clave | Preguntar al usuario (posiblemente testing/validacion sin codigo, o ajuste manual en produccion) |

**IMPORTANTE**: Siempre verificar la autoria con `%an <%ae>` en el formato de git log. Nunca asumir autoria sin confirmar.

Para commits encontrados, extraer la descripcion tecnica del mensaje del commit:
```bash
git -C "<repo>" log <commit_hash> -1 --format="%s%n%b"
```

### Paso 5: Clasificar complejidad para estimacion "Sin IA"

Usar la siguiente escala de multiplicadores:

| Complejidad | Multiplicador | Criterio |
|---|---|---|
| **Revision** | 1.3x | Revision de PR ajeno: lectura y validacion de codigo ya escrito, sin autoria propia del cambio |
| **Baja** | 1.5x | Fix puntual: 1 archivo, 1 campo, atributo faltante, ajuste simple |
| **Media** | 2.3x | Analisis multi-modulo, queries SQL, flujo entre capas, migracion de customs |
| **Alta** | 2.7x | Cambio de tipos de datos, regresiones con multiples iteraciones fix-test-fail, correccion de datos existentes via SQL |

Para **migraciones tecnicas de modulos custom** (bloques sin ticket del Paso 2b), el multiplicador por defecto es Media (2.3x) salvo que las señales de abajo empujen a Alta (ej. migracion con muchas iteraciones fix-test-fail o cambios de tipos de datos entre versiones).

**Señales objetivas de apoyo** (no reemplazan el criterio final, pero evitan que la clasificacion dependa solo de memoria/intuicion — ya estan disponibles de los pasos 3-4, no requieren trabajo adicional):
- **Cantidad de fechas distintas entre los commits del ticket** (`git -C "<repo>" log --grep="<numero_ticket>" --format=%ad --date=short`): mas de 1 fecha distinta sugiere iteracion fix-test-fail → empuja hacia Alta.
- **Cantidad de modulos/repos tocados** (`git -C "<repo>" show --stat <hash>` de cada commit del ticket): 1 modulo → Baja; 2+ modulos, o cruza de un custom a un submodulo (`integra-addons`/`odoo-venezuela`) → Media o Alta.
- **Dias calendario entre el primer y el ultimo commit del ticket**: mismo dia → Baja/Media; varios dias → señal de Alta.

Usar estas señales como checklist antes de asignar el tier, no como formula automatica — el criterio final sigue siendo del usuario. Si el tier elegido no coincide con lo que sugieren las señales (ej. se clasifica Baja pero hubo commits en 3 fechas distintas), preguntar o dejar constancia de por que aplica la excepcion.

### Paso 6: Preguntar al usuario sobre tickets y bloques dudosos

**ANTES de generar el HTML**, presentar una tabla con:

1. Tickets y bloques sin ticket que cumplen el criterio (incluir), separando cuales son Desarrollo propio y cuales son Revision de PR
2. Tickets/bloques en el rango de fecha pero sin commits ni merges del autor (preguntar)
3. Tickets con commits de otros autores y sin revision/merge propia (preguntar si excluir)
4. Tickets/bloques sin ninguna evidencia en absoluto (preguntar)

Ejemplo de formato de consulta:
```
### A incluir como Desarrollo propio (6):
TI_13686, TI_13461, TI_13387, TI_13574, TI_13573, TA_73536

### A incluir como Revision de PR (2):
TI_13159 (merge de PR #204, autor del cambio: otro dev)
"Migracion tecnica Bodegon v16→v19" (bloque sin ticket, agrupado de 3 sesiones)

### Dudosos en el periodo — ¿que hago con ellos?
1. TI_13577 — commits encontrados pero de otro autor (rsgg04), sin revision propia visible, excluir?
2. TI_13656 — sin commits locales (pruebas con BK segun hoja), excluir?
3. "Ajuste Reporte Z / Libro de Ventas" (sin ticket) — sin commit por palabra clave en el periodo, incluir igual con nota o excluir?
```

### Paso 7: Generar el HTML

Leer la plantilla con la tool Read desde `.claude/skills/reporte-horas-ia/template.html` y reemplazar los placeholders:

```
{{PERIODO}}         → "15 al 30 de junio de 2026"
{{EMPLEADO}}        → "Roger Vera"
{{FILAS}}           → bloques <tr> generados para cada ticket
{{TOTAL_CON_IA}}    → suma total de horas con IA
{{TOTAL_SIN_IA}}    → suma total de horas sin IA
```

**Formato de cada fila:**
```html
<tr>
  <td class="ti">{{NRO_TI_TA}}</td>
  <td class="tt">{{TITULO_TICKET}}</td>
  <td>{{DESCRIPCION}}</td>
  <td class="hr">{{HORAS_CON_IA}} h</td>
  <td>{{IMPACTO_SIN_IA}}</td>
  <td class="hr">{{HORAS_SIN_IA}} h</td>
</tr>
```

Donde:
- `{{NRO_TI_TA}}` = `TI_XXXXX` o `TA_XXXXX` (con underscore, sin espacio); para bloques sin ticket usar `S/T`
- `{{TITULO_TICKET}}` = titulo descriptivo corto (max ~60 chars)
- `{{DESCRIPCION}}` = basada en commit message + notas de la hoja de horas
- `{{HORAS_CON_IA}}` = horas de la hoja de horas para ese ticket
- `{{IMPACTO_SIN_IA}}` = descripcion de lo que habria costado sin asistencia de IA
- `{{HORAS_SIN_IA}}` = horas * multiplicador (redondeado a .0 o .5)

**IMPORTANTE**: La columna `Mayor impacto sin IA` debe describir concretamente que tareas especificas habrian sido mas lentas sin IA, no frases genericas. Ejemplos:
- Bien: "Navegacion y rastreo del query SQL entre modulos homologados: entender la estructura de _get_balances sin sugerencias de codigo"
- Mal: "El trabajo sin IA habria tomado mas tiempo"

Guardar el HTML generado como archivo con Write tool, con nombre sugerido:
```
reporte-horas-<periodo-corto>-<empleado>.html
```

### Reglas importantes

1. **Incluir tickets con desarrollo propio, revision de PR (con evidencia de merge/autor del cambio), e incidencias o migraciones sin ticket con commits identificables por palabra clave** — no limitarse a filas que traigan numero TI/TA
2. **Excluir** ausencias, tiempo personal, reuniones, redaccion de informes, feedback/charlas internas
3. **TA_** para tareas (ej: TA_73536), **TI_** para tickets (ej: TI_13387), **S/T** para bloques de trabajo sin ticket
4. **Horas con decimales**: usar formato `X.X h` o `X.XX h`
5. **Nunca inventar commits ni merges**: si no se encuentra ninguno (ni por ticket ni por palabra clave), reportarlo como "sin commits" y preguntar (Paso 6), no descartar en silencio
6. **Verificar submodulos**: muchos fixes estan en `integra-addons/` u `odoo-venezuela/`, no en el repo principal
7. **Registro historico para recalibrar los multiplicadores**: ademas del HTML, appendear una fila por ticket a un CSV acumulativo `reporte-horas-historico.csv` (columnas: `fecha_reporte,ticket,complejidad,multiplicador,horas_con_ia,horas_sin_ia`) en el mismo directorio donde se guarda el HTML — crear el archivo con encabezado si no existe. Sirve para revisar cada tanto (ej. trimestral) si 1.5x/2.3x/2.7x siguen siendo realistas en vez de asumir que las constantes originales son correctas para siempre.
