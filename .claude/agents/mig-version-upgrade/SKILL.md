---
name: mig-version-upgrade
description: Evalua si los modulos custom de un proyecto Odoo siguen siendo estructuralmente validos en una version de Odoo destino (ej. 16 a 17), y genera una lista de cambios clasificada por riesgo cuando no lo son -- incluyendo si sus dependencias a integra-addons/odoo-venezuela son compatibles con integra en la version destino. Usar cuando el usuario pida evaluar o preparar la migracion de version de un proyecto cliente, o pregunte que tan lista esta una version de Odoo destino para un cliente especifico. Funciona en modo diagnostico: no reescribe modulos de alto riesgo sin aprobacion.
---

# mig-version-upgrade

Evalua la superficie de los modulos custom de un proyecto cliente contra una version de Odoo destino, y produce un reporte de compatibilidad + una lista de cambios accionable. No es un migrador automatico de codigo: los cambios mecanicos de bajo riesgo se aplican con aprobacion, los de alto riesgo (reescrituras de frontend, snippets) se documentan para que un desarrollador los resuelva.

Reutiliza, sin duplicar su logica: `project-type-detect` (Paso 0), `verificar-referencia-modulo` (Paso 3, modo cross-version), `odoo-16-to-17-migration` (Paso 4, motor de ejecucion mecanica cuando el salto es 16.0→17.0).

**Version 1 -- piloto.** Este skill nace para un salto corto (16→17) sobre un proyecto real (`bodegonactual`) con el objetivo explicito de refinarlo antes de intentar saltos mas largos (17→18, 18→19). Cada corrida real debe alimentar el checklist versionado (ver Paso 2) con lo que se haya aprendido -- si el skill no encuentra algo que el desarrollador si encuentra a mano, es una senal de que el checklist o el Paso 1 estan incompletos, no que el enfoque este mal.

## Informacion necesaria

1. **Proyecto objetivo** -- *derivable*, misma resolucion que `project-type-detect` (cwd con `.gitmodules` propio, o `src/custom/<nombre>` desde la raiz de docker-odoo).
2. **Version destino** -- *preguntar siempre*, no asumir. No tiene por que ser la version inmediata siguiente.
3. **Modulos custom en alcance** -- *preguntar siempre* (ver Paso 0). Nunca asumir que todo lo que hay en el repo esta instalado.

## Paso 0 -- Entorno, comparables y alcance

1. Aplicar `project-type-detect`: tipo de proyecto (Homologado/Operativo), `odoo_version` origen, submodulos presentes.
2. Verificar que exista una rama de mantenimiento para la version destino en cada submodulo relevante (sin checkout, ver `verificar-referencia-modulo`):
   ```bash
   git -C <submodulo> ls-remote --heads origin | grep -E "<version_destino>(\.0)?$"
   ```
   Si `integra-addons` (Operativo) o `integra-addons`+`odoo-venezuela` (Homologado) no tienen rama para la version destino, **detenerse y avisar** -- no tiene sentido evaluar compatibilidad contra algo que no existe todavia.
3. Verificar disponibilidad local de nucleo Odoo/Enterprise en la version destino (`src/enterprise-<version_destino>` desde la raiz de docker-odoo, y el repo `src/odoo` en esa rama/tag) -- se usan en el Paso 2 para diffear cambios estructurales reales en vez de depender solo de una lista memorizada.
4. Listar TODOS los modulos custom detectados (carpetas con `__manifest__.py` en la raiz del proyecto, excluyendo submodulos) y preguntar al usuario, con `AskUserQuestion`, cuales estan **realmente instalados/en uso** en el cliente. No asumir que todos lo estan -- puede haber modulos descontinuados, de prueba, o remanentes de otro cliente. Todo el resto del proceso (Pasos 1-4) se limita a los modulos confirmados; los demas se listan en el reporte final bajo "Excluidos del alcance -- no instalados", sin analizarlos.
5. **Rama de trabajo del repo del cliente**: antes de tocar cualquier archivo, verificar si ya existe una rama `mg_stg_<version_destino>` (local o remota, `git branch -r | grep -i mg_stg`) para este proyecto.
   - Si existe, partir de ahi (es la rama de migracion ya establecida -- ver `branch-create`, seccion "Caso especial: proyectos en migracion de version").
   - Si NO existe todavia (caso tipico de la primera corrida de este skill sobre un proyecto), **esta corrida es la que la establece**: crear `mg_stg_<version_destino>` (ej. `mg_stg_17.0`, o `mg_stg_l10nve_<version_destino>` si es Homologado) directamente desde la rama de release/staging actual del cliente -- **no** invocar `branch-create` en su modo generico de rama de trabajo (tipo/ti-ta/nombre-en-ingles), porque esa skill no tiene forma de saber por si sola que este es el caso especial de migracion si todavia no existe ninguna rama `mg_stg_` que detectar. Si mas adelante hace falta una sub-rama para un ticket/tarea puntual dentro de la migracion, ahi si partir de esta `mg_stg_<version_destino>` como `origen` y usar `branch-create` normalmente.
   - Mostrar el nombre exacto de la rama antes de crearla, como cualquier creacion de rama.

## Paso 1 -- Inventario de superficie por modulo (solo modulos en alcance)

Por cada modulo confirmado en el Paso 0.4, extraer:
- `depends` en `__manifest__.py` (marcar cuales son `binaural_*`/`l10n_ve_*` -- van al Paso 3).
- Claves de `assets` declaradas (bundles JS/SCSS/XML).
- Modelos con `_inherit`/`_inherits` en Python, especialmente sobre `point_of_sale`, `website`, o cualquier modulo core que el checklist del Paso 2 marque como refactorizado en el salto de version.
- Vistas XML: uso de `attrs=`/`states=`, tipo de tag raiz (`tree`/`list`, etc.), `t-esc`/`t-out`.
- JS/OWL propio (`static/src/js`, `static/src/components`, `static/src/xml`) -- es la superficie de mayor riesgo real, un simple grep de `_inherit` en Python no la detecta.
- Reportes QWeb (`report/*.xml`).
- Seguridad (`ir.model.access.csv`, `ir.rule`) y datos/cron.

## Paso 2 -- Checklist de compatibilidad estructural del salto de version

Leer primero `docker-odoo/upgrade/checklists/<origen>-<destino>.md` (ej. `16.0-17.0.md`) como base de reglas conocidas -- mismo principio que el estandar OpenSpec+Tests: se lee antes de generar, y se enriquece con cada corrida real. Si no existe el checklist para ese salto especifico, crearlo con las reglas que se descubran en esta corrida.

Para cada item de superficie del Paso 1, cruzarlo contra el checklist. Cuando el checklist no cubra algo que el diff real de `src/enterprise-<origen>` vs `src/enterprise-<destino>` (o `src/odoo`) muestre como cambiado -- ej. un bundle de assets renombrado, una vista que cambio de motor, un decorador removido -- agregarlo como propuesta de nueva entrada al checklist (mostrar el diff al usuario antes de darlo por valido).

Clasificar cada hallazgo:
- **Bloqueante**: el modulo no cargaria en destino (API/campo removido, bundle inexistente, vista referenciando algo que ya no existe).
- **Recomendado**: funciona pero usa una forma deprecada (ej. `attrs=`/`states=`).
- **Informativo**: cambio de comportamiento sin romper carga (ej. estilo visual).

## Paso 3 -- Compatibilidad con integra/homologado destino

Para cada dependencia `binaural_*` (Operativo) o `l10n_ve_*` (Homologado) detectada en el Paso 1, aplicar `verificar-referencia-modulo` en **modo cross-version**: ubicacion remota `<submodulo>@<rama_destino>:<modulo>.<external_id si aplica>`.

Mapear el veredicto:
- FUNCIONAL → ✅ Compatible, sin cambio.
- RENOMBRADO → ⚠️ actualizar referencia al candidato reportado (mostrar antes/despues).
- HUERFANO → ❌ Bloqueante -- integra/homologado destino no tiene el modulo migrado todavia a esa version. Esto bloquea la migracion del custom completo hasta que integra-addons/odoo-venezuela publiquen ese modulo en la version destino; reportarlo como dependencia externa, no como algo que el custom pueda resolver solo.

## Paso 4 -- Lista de cambios y aplicacion

- **Bajo riesgo / mecanico** (ej. `attrs=`/`states=`, renombres de bundle 1:1 confirmados en el checklist): **no reimplementar las reglas de conversion aca**. Cuando el salto sea 16.0→17.0, invocar la skill `odoo-16-to-17-migration` (con la tool Skill) pasandole la lista de modulos ya confirmada en el Paso 0.4 como alcance -- ella se encarga de bump de manifest, `attrs=`/`states=` a expresiones inline, typos y atributos deprecados (`no_open`/`no_create_edit`), mostrando el diff. Para saltos todavia sin skill ejecutora dedicada (17→18, 18→19), aplicar el cambio mecanico directamente mostrando el diff, igual que antes. En ambos casos, despues de aplicar, validar con `./odoo update` sobre el modulo afectado en la version destino (ver skill `odoo-testing`, plugin `binaural-fn-programador`) — un cambio "mecanico" que no carga sigue siendo Bloqueante, no Recomendado.
- **Alto riesgo** (reescritura de JS/OWL, snippets de website, cualquier cosa marcada Bloqueante sin un patron de fix conocido en el checklist): **no aplicar solo**. Documentar el hallazgo con el ejemplo antes/despues si el checklist ya tiene el patron (ej. `Registries.Model.extend` → `patch()` de `@web/core/utils/patch`), y dejarlo como tarea manual para un desarrollador.
- **Si se bumpea el campo `'version'` de los manifests** (necesario para que `docker-odoo-add-instance` derive el `odoo_version` correcto al armar una instancia de prueba real): validar el resultado contra la regla real de Odoo (`odoo/modules/module.py: adapt_version()`, ver checklist item 12) -- despues del prefijo de serie (`<version_destino>.`) deben quedar **al menos dos numeros** (`x.y` o `x.y.z`). Un bump ingenuo tipo `16.7` → `17.0.7` (un solo numero final) revienta en runtime con `ValueError: Invalid version`. Verificar con el regex `^[0-9]+\.[0-9]+(?:\.[0-9]+)?$` sobre lo que queda tras el prefijo antes de dar el bump por bueno, no solo anteponer la serie nueva. Si se delego en `odoo-16-to-17-migration`, ella ya aplica esta regla en su Fase 1 -- no volver a bumpear.

## Paso 5 -- Reporte final

Tabla por modulo (mismo espiritu que `mig-customs-to-homo`):

| Modulo | Veredicto | Detalle |
|---|---|---|
| ✅ Valido sin cambios | No se encontro nada bloqueante ni recomendado. |
| ⚠️ Requiere cambios menores (aplicados) | Cambios mecanicos ya aplicados, listar archivos. |
| 🔶 Requiere reescritura mayor (manual) | Alto riesgo, no aplicado -- listar hallazgos y referencia al checklist. |
| ❌ Bloqueado por dependencia no migrada | Al menos una dependencia HUERFANO en integra/homologado destino. |

Incluir tambien:
- Modulos excluidos del alcance (Paso 0.4), sin analizar.

**Confirmacion obligatoria de los 🔶 (no solo mencionarlos en la tabla)**: si hay al menos un modulo en 🔶 Requiere reescritura mayor, cerrar el reporte con una seccion aparte, visible, que liste cada uno con: que archivo(s) puntualmente, que patron de fix se conoce (si el checklist ya lo tiene) o que no se conoce todavia, y una estimacion de alcance (ej. "6 archivos JS, reescritura completa" vs "1 archivo, xpath a reubicar"). Terminar esa seccion pidiendole EXPLICITAMENTE al usuario que confirme haber visto la lista antes de dar la corrida por cerrada -- no alcanza con que quede como parrafo informativo dentro del reporte largo; tiene que ser una pregunta real (`AskUserQuestion` o texto directo) que el usuario conteste, igual que los demas puntos de control. El motivo: estos son los items que un desarrollador va a tener que agarrar aparte, y si quedan enterrados en la tabla es facil que se pierdan de vista al pasar del diagnostico a la ejecucion real.
- Nuevas entradas propuestas al checklist de esta corrida (si las hubo), para que el usuario las confirme antes de guardarlas en `docker-odoo/upgrade/checklists/<origen>-<destino>.md`.

## Puntos de control (siempre pedir confirmacion explicita antes de)

- Paso 0.4: la lista de modulos en alcance, antes de analizar nada.
- Paso 2: cualquier entrada nueva propuesta al checklist compartido, antes de guardarla (afecta a futuras corridas de otros proyectos).
- Paso 4: aplicar cambios mecanicos de bajo riesgo, mostrando el diff antes de escribir.
- Paso 5: la lista de modulos 🔶 (reescritura mayor manual) -- pedir confirmacion explicita de que el usuario la vio, no darla por leida solo porque aparece en la tabla del reporte (ver Paso 5).
- Nunca aplicar cambios de alto riesgo sin que el usuario lo pida explicitamente modulo por modulo.
