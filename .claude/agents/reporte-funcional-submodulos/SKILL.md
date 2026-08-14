---
name: reporte-funcional-submodulos
description: Genera un PDF de solo lectura que analiza los tickets/commits incluidos en una actualizacion de submodulos (integra-addons, odoo-venezuela, third-party-addons), documentando Resumen/Problema/Causa/Solucion de cada uno y un veredicto de si el fix es realmente funcional o podria introducir otro problema. Usar cuando el usuario pida el informe funcional/de auditoria posterior a una actualizacion de submodulos, o quiera validar de forma independiente y solo-lectura los tickets que trajo un bump de tag.
---

# reporte-funcional-submodulos

Extiende el patron de `reporte-incidencias-higea` (mismo script mecanico, mismo criterio de redaccion, mismo mecanismo de entrega) agregando lo que una actualizacion de submodulos necesita de mas: no solo documentar cada incidencia, sino **leer el diff real y opinar si la solucion aplicada resuelve el problema sin introducir otro**.

Esta skill es **estrictamente de solo lectura**: nunca ejecuta `git commit`, `git push`, `git checkout` de ramas, ni modifica ningun archivo del repo o de los submodulos. Solo usa `git log`/`git show`/`git diff`/`git blame` para leer. Esto la hace segura de correr en cualquier modo de permisos — incluyendo una sesion aparte con permisos omitidos, si el usuario prefiere invocarla manualmente en vez de dejar que `submodule-update` la lance en background al terminar un bump.

## Restriccion de datos (obligatoria)

Igual que `reporte-incidencias-higea`: el HTML y el PDF se generan y entregan en el filesystem del usuario (`SendUserFile`), nunca se suben a un servicio externo. **No usar la tool `Artifact`** ni ninguna otra que publique el contenido fuera de la maquina del usuario — los datos de la empresa/cliente no deben salir de la organizacion.

## Paso 1 — Determinar el alcance

Si esta skill fue lanzada por `submodule-update` (Paso 10 de esa skill), el prompt ya trae: proyecto, y por submodulo su ruta y su rango `<sha_anterior>..<tag_nuevo>`. Usar eso directamente, sin volver a preguntar.

Si se invoca suelta, se necesita por cada submodulo a auditar:
1. **Rango**: `--range <sha1>..<sha2>` (o dos tags). Si el usuario no lo da, preguntar — no asumir un rango arbitrario.
2. **Repositorio**: ruta al submodulo (ej. `src/custom/higea/integra-addons`).

## Paso 2 — Extraer los commits

Reutilizar tal cual el script ya existente de `reporte-incidencias-higea` (no duplicarlo ni copiarlo):
```bash
python3 ~/.claude/agents/reporte-incidencias-higea/extract_commits.py \
  --repo <ruta_submodulo> --range <sha_anterior>..<tag_nuevo> \
  --tags FIX,FEAT,HOTFIX,MIG
```
Se amplia la lista de tags por defecto respecto a `reporte-incidencias-higea` (que usa `FIX,FEAT`) porque un bump de submodulo tipicamente arrastra tambien `HOTFIX` y `MIG` (migraciones/homologaciones) ya mergeados a la rama de mantenimiento.

Si devuelve `0 commits`, avisar y verificar el rango antes de seguir.

## Paso 3 — Redactar cada incidencia (mismo criterio que reporte-incidencias-higea)

Aplicar exactamente el mismo criterio de filtrado y redaccion de `reporte-incidencias-higea` (Paso 3 de esa skill): excluir ruido tecnico (bumps de manifest, ajustes de lint), fusionar commits que son la misma incidencia con una regresion posterior, y redactar **Resumen / Problema / Causa / Solucion** en prosa clara a partir del cuerpo del commit y, si hace falta mas contexto, del diff (`git show <hash>`).

Ante la duda de si un commit es o no una incidencia real, preguntar al usuario en vez de decidir en silencio.

## Paso 4 — Veredicto funcional (lo nuevo de esta skill)

Para cada incidencia que quedo en el Paso 3, ademas de los 4 campos, leer el diff completo (`git show <hash>`, y si el fix toca varios commits, todos los involucrados) y emitir un veredicto:

| Veredicto | Cuando aplica |
|---|---|
| **Funcional** | El diff resuelve el problema descrito de forma consistente con la causa raiz explicada; no se observan casos no cubiertos ni efectos secundarios evidentes sobre el mismo flujo. |
| **Con riesgo detectado** | El fix resuelve el sintoma reportado pero el diff deja ver un caso no cubierto, un efecto secundario probable en otro flujo, o una condicion (ej. un `if`/`compute` sin `else` explicito, un default que no cubre todos los casos) que podria reproducir el mismo problema u otro distinto bajo otras condiciones. Explicar concretamente cual es el riesgo y en que escenario se manifestaria. |
| **Requiere revision** | El diff no alcanza para juzgar con confianza (contexto insuficiente, cambio en un area no relacionada al ticket, o el commit referenciado no se encuentra en el rango) — no inventar un veredicto favorable por defecto. |

Reglas:
- **Nunca inventar un riesgo ni una confirmacion sin evidencia en el diff.** Si el veredicto es "Con riesgo detectado", citar la linea/funcion concreta que lo sustenta.
- Si una incidencia del Paso 3 ya es la fusion de un fix + su regresion posterior, el veredicto se emite sobre el estado **final** (el ultimo commit de esa fusion), no sobre el intento intermedio.
- Si hay commits posteriores en la MISMA rama de mantenimiento (fuera del rango pedido) que corrigen algo de esta incidencia, mencionarlo como nota aparte, pero el veredicto sigue siendo sobre lo que efectivamente entro en este bump.

## Paso 5 — Armar el HTML

Leer `~/.claude/agents/reporte-funcional-submodulos/template.html` con la tool Read y reemplazar los placeholders — mismo mecanismo que `reporte-incidencias-higea`, agregando el campo de veredicto:

```
{{TITULO}}               -> ej. "Informe Funcional de Actualizacion de Submodulos - Higea"
{{PERIODO}}               -> ej. "commit abc123 a l10nve_17.0.2.2.0-beta.6 (integra-addons)"
{{FECHA_GENERACION}}       -> fecha de hoy
{{FUENTE}}                 -> ej. "integra-addons, odoo-venezuela, third-party-addons - proyecto higea"
{{FILAS_RESUMEN}}          -> un <tr> por incidencia, incluyendo columna de veredicto
{{INCIDENCIAS_DETALLE}}    -> un bloque <div class="incident"> por incidencia, con el campo Veredicto
{{NOTA_PIE}}               -> nota de alcance: que se excluyo y por que, y que esta skill es de solo lectura
```

Fila de la tabla resumen (agrega columna de veredicto respecto a `reporte-incidencias-higea`):
```html
<tr>
  <td>{{N}}</td><td>{{FECHA}}</td><td><code>{{MODULO}}</code></td><td>{{RESUMEN}}</td><td>{{TICKET}}</td>
  <td class="veredicto-{{VEREDICTO_CLASE}}">{{VEREDICTO}}</td>
</tr>
```

Bloque de detalle por incidencia:
```html
<div class="incident">
  <h2>{{N}}. {{TITULO_INCIDENCIA}}</h2>
  <div class="meta"><span>Modulo: {{MODULO}}</span><span>Fecha: {{FECHA}}</span><span>Commit: {{HASH}}</span></div>
  <div class="field"><span class="label">Resumen:</span> {{RESUMEN}}</div>
  <div class="field"><span class="label">Problema:</span> {{PROBLEMA}}</div>
  <div class="field"><span class="label">Causa:</span> {{CAUSA}}</div>
  <div class="field"><span class="label">Solucion:</span> {{SOLUCION}}</div>
  <div class="field veredicto-{{VEREDICTO_CLASE}}"><span class="label">Veredicto funcional:</span> {{VEREDICTO}} — {{VEREDICTO_JUSTIFICACION}}</div>
</div>
```

Guardar el HTML con la tool Write en el directorio scratchpad de la sesion (no en el repo del proyecto).

## Paso 6 — Convertir a PDF y entregar

```bash
weasyprint <ruta_scratchpad>/informe_funcional_<slug>.html <ruta_scratchpad>/informe_funcional_<slug>.pdf
```
Entregar con `SendUserFile` (nunca con `Artifact`). Mencionar cuantas incidencias quedaron, cuantas tuvieron veredicto "Con riesgo detectado" o "Requiere revision" (destacarlas primero en el mensaje al usuario, son las que mas le importan), y si se excluyo algo relevante del rango original.

**Si esta skill corre como subagente (lanzada via la tool `Agent`, ej. desde `submodule-update`) y `SendUserFile` no esta disponible en ese entorno**: no es un bloqueo — nunca dejar el informe a medias ni terminar el turno diciendo que se "esta esperando" algo. Completar igual todos los pasos (HTML, PDF), dejar el PDF y el HTML en el directorio scratchpad de la sesion, y en el resumen final devuelto por el subagente indicar explicitamente la ruta completa del PDF para que quien orquesto la llamada (la sesion principal, que si tiene `SendUserFile`) lo relaye al usuario.

## Paso 7 — Archivar en la biblioteca global

Después de entregar el PDF, archivar cada incidencia documentada en el Paso 3/4 en la biblioteca global de submódulos siguiendo las reglas de la skill `biblioteca-submodulos` (`~/.claude/agents/biblioteca-submodulos/SKILL.md`, sección "Modo archivado") — **reutilizar los campos ya redactados, no volver a analizar el diff**. Esto es lo que permite, en corridas futuras, detectar automáticamente cuando un tag nuevo resuelve algo que antes quedó marcado como riesgo en otro proyecto.

Si esta skill corre como subagente y no tiene acceso de escritura a `~/binaural/biblioteca-submodulos/` por algún motivo, no es un bloqueo — completar igual el resto del informe y mencionar explícitamente en el resumen final qué incidencias no se pudieron archivar, para que la sesión que orquestó la llamada lo haga en su lugar.

En el resumen final que se le devuelve al usuario, destacar cualquier incidencia que haya pasado de `abierto`/`monitoreo` a `resuelto` en esta corrida (ver regla de `biblioteca-submodulos`) — es una señal directa de "esto es lo que este tag arregló", que es justo lo que hace valiosa la biblioteca.

## Reglas importantes

1. **El script no decide contenido** (igual que en `reporte-incidencias-higea`): `extract_commits.py` solo hace `git log` + parseo mecanico. Toda sintesis de campos y todo veredicto funcional es responsabilidad de quien ejecuta la skill.
2. **Nunca escribir**: sin `git commit`/`push`/`checkout` de ramas, sin editar archivos del repo — solo lectura de principio a fin.
3. **Nunca inventar una incidencia, un ticket o un veredicto favorable sin evidencia** — ante la duda, "Requiere revision" en vez de "Funcional".
4. **Nunca subir el HTML/PDF a un servicio externo**: se entrega solo con `SendUserFile`, se guarda solo en el scratchpad de la sesion.
5. **Fondo blanco explicito** en `template.html` (igual que en `reporte-incidencias-higea`) para evitar inversion de colores en visores con modo oscuro.
