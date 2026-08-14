---
name: biblioteca-submodulos
description: Mantiene y consulta la biblioteca global (fuera del repo, en ~/binaural/biblioteca-submodulos) de incidencias/riesgos/mejoras detectadas en los submodulos compartidos integra-addons, odoo-venezuela y third-party-addons. Usar SIEMPRE antes de empezar a resolver un ticket en cualquier proyecto de docker-odoo para verificar si ya es un problema conocido en estos submodulos, y automaticamente en background (desde reporte-funcional-submodulos, Paso 7 de esa skill) para archivar los hallazgos de cada actualizacion de submodulos.
---

# biblioteca-submodulos

Biblioteca **global** (no por cliente) de incidencias documentadas en los submódulos compartidos `integra-addons`, `odoo-venezuela` y `third-party-addons`. Vive en `~/binaural/biblioteca-submodulos/` (fuera de `docker-odoo`, ver el `README.md` de esa carpeta para el por qué). Dos modos de uso: **consulta** (lectura, cuando el usuario presenta un ticket) y **archivado** (escritura, alimentado desde `reporte-funcional-submodulos`).

## Estructura de la biblioteca

```
~/binaural/biblioteca-submodulos/
  README.md
  INDEX.md
  integra-addons/<modulo_odoo>/<ticket_o_slug>.md
  odoo-venezuela/<modulo_odoo>/<ticket_o_slug>.md
  third-party-addons/<modulo_odoo>/<ticket_o_slug>.md
```

- `<modulo_odoo>`: el módulo real dentro del submódulo (ej. `l10n_ve_accountant`, `binaural_account_reports`), no el nombre del submódulo.
- `<ticket_o_slug>`: número de ticket de Binaural helpdesk si existe (ej. `13694.md`); si el commit no tiene ticket (hotfix sin ticket, o commit histórico sin referencia), usar un slug corto en inglés derivado del asunto + hash corto (ej. `advance-payment-cross-error-3a2c76f6.md`).

## Formato de cada entrada

```markdown
---
ticket: 13694
modulo: l10n_ve_accountant
submodulo: odoo-venezuela
veredicto: riesgo
estado: abierto
detectado_en:
  - proyecto: countryclub-17.0
    tag: 17.0.2.0.7-beta.8
    fecha: 2026-08-05
    commits: [a03f74eb6, adfc269d0]
resuelto_en: null
---

## Resumen
...
## Problema
...
## Causa
...
## Solucion
...
## Veredicto funcional
...
```

Campos:
- **veredicto**: `funcional` | `riesgo` | `revision` — el mismo vocabulario de `reporte-funcional-submodulos` (Funcional / Con riesgo detectado / Requiere revisión).
- **estado**: `abierto` (riesgo o revisión pendiente, sin fix confirmado todavía), `resuelto` (un tag posterior ya lo corrigió, ver `resuelto_en`), `monitoreo` (parcialmente corregido, o corregido pero sin confirmar en producción todavía). Las entradas con veredicto `funcional` nacen con `estado: resuelto` directamente (ya se archivan como mejora, no como pendiente).
- **detectado_en**: **lista**, no un solo valor — la misma incidencia puede volver a aparecer en la actualización de otro proyecto cliente en otro momento (son submódulos compartidos). Cada vez que se re-detecta, se **agrega** un elemento a esta lista en vez de crear un archivo duplicado.
- **resuelto_en**: `null` mientras `estado` sea `abierto`. Cuando se confirma la corrección: `{tag, fecha, proyecto, commit}`.

## Modo consulta (lectura — usar antes de resolver cualquier ticket)

Antes de empezar a diagnosticar o corregir un ticket en **cualquier** proyecto de `docker-odoo` que involucre código de `integra-addons`, `odoo-venezuela` o `third-party-addons` (no solo durante una actualización de submódulos):

1. Buscar por número de ticket si el usuario ya dio uno:
   ```bash
   grep -rl "ticket: <numero>" ~/binaural/biblioteca-submodulos/
   ```
2. Si no hay ticket o no aparece nada, buscar por módulo/palabra clave del problema (nombre de método, síntoma):
   ```bash
   grep -ril "<palabra_clave>" ~/binaural/biblioteca-submodulos/<submodulo>/
   ```
3. Si aparece una entrada relacionada (mismo módulo, mismo método, síntoma parecido): leerla completa antes de proponer una solución. Si su `estado` es `abierto` o `monitoreo`, decirle explícitamente al usuario que ya hay un riesgo conocido documentado ahí (con la ruta del archivo) antes de continuar — puede cambiar el diagnóstico o evitar repetir un fix que ya se sabe insuficiente (ver ejemplo real: Ticket 13744 en `l10n_ve_iot_mf`, donde un primer fix quedó documentado como incompleto y un commit posterior tuvo que restaurar lógica que el primero había quitado).
4. Si la entrada existe pero está `resuelta` en un tag más nuevo que el que tiene el proyecto actual, mencionarlo — puede ser más rápido actualizar el submódulo a ese tag que resolver el ticket de nuevo desde cero.
5. Si no aparece nada relevante, seguir el flujo normal de diagnóstico — no forzar una relación que no existe.

**Nunca modificar la biblioteca en modo consulta** — es de solo lectura en este flujo.

## Modo archivado (escritura — invocado desde reporte-funcional-submodulos)

Ejecutado como parte del Paso 7 de `reporte-funcional-submodulos`, reutilizando los campos Resumen/Problema/Causa/Solución/Veredicto ya redactados por esa skill para cada incidencia — **no se vuelve a analizar el diff ni se redacta de nuevo**, solo se archiva lo ya producido.

Para cada incidencia del informe recién generado:

1. **Determinar la clave de deduplicación**: número de ticket si existe; si no, slug de asunto+hash.
2. **Buscar si ya existe** una entrada con esa clave en `~/binaural/biblioteca-submodulos/<submodulo>/<modulo>/`:
   - **No existe** → crear el archivo nuevo con el formato de arriba, `detectado_en` con un solo elemento (este proyecto/tag/commits), `estado` según el veredicto (`funcional`→`resuelto`, `riesgo`/`revision`→`abierto`).
   - **Ya existe** → leer la entrada existente:
     - Si el `estado` previo era `abierto`/`monitoreo` y el veredicto de esta nueva pasada es `funcional` (es decir, el mismo commit/ticket que antes se marcó riesgoso ahora aparece corregido en un tag más nuevo) → actualizar `estado: resuelto` y llenar `resuelto_en` con el tag/proyecto/commit actual. Mencionar esto explícitamente en el resumen final que la skill le devuelve al usuario ("Ticket X, marcado como riesgo en `<tag anterior>`, aparece resuelto en `<tag nuevo>`") — es exactamente el seguimiento que pidió el usuario.
     - Si el veredicto es el mismo que ya tenía (ej. sigue `riesgo`) → solo agregar el proyecto/tag/commits actuales a la lista `detectado_en`, sin duplicar el contenido narrativo (a menos que el nuevo commit agregue información relevante que no estaba, en cuyo caso ampliar el campo correspondiente).
3. **Actualizar `INDEX.md`**: agregar fila si es una entrada nueva, o actualizar la fila existente (veredicto/estado/última actualización/proyectos) si ya existía. Mantener el índice como fuente rápida de escaneo, no reescribir entradas que no cambiaron.

## Reglas importantes

1. **Nunca inventar una relación entre incidencias** que no esté respaldada por el mismo ticket, el mismo método, o el mismo síntoma explícito en los mensajes de commit — ante la duda, tratarlas como entradas separadas.
2. **La biblioteca no sale de la máquina del usuario**: son archivos locales en `~/binaural/`, nunca se sube a un servicio externo ni se usa `Artifact` sobre su contenido.
3. **El archivado nunca vuelve a redactar el diff** — reutiliza lo que ya produjo `reporte-funcional-submodulos` (o quien sea que esté archivando), para no duplicar el trabajo de análisis ni arriesgar veredictos inconsistentes entre el informe PDF y la biblioteca.
