---
name: git-flow
description: Ejecuta el flujo completo Rama -> Commit -> PR para un ticket o tarea, orquestando en orden las skills branch-create, commit-message y pr-create. Usar cuando el usuario pida empezar a trabajar un ticket/tarea de punta a punta, o pida "crear la rama, el commit y el PR" en un solo pedido.
---

# git-flow

Orquesta el flujo completo de trabajo para un cambio: **1) crear la rama -> 2) hacer el commit -> 3) push + crear el PR**, en ese orden, reutilizando la logica de las skills individuales:

- Paso 1: `branch-create`
- Paso 2: `commit-message`
- Paso 3: `pr-create`

Cada paso se ejecuta solo despues de que el paso anterior este confirmado y completo. **Nunca saltar directamente al paso 3 sin haber completado 1 y 2**, y nunca ejecutar push o `gh pr create` sin aprobacion explicita del usuario en ese momento (la aprobacion de un paso no autoriza los siguientes).

## Recoleccion de informacion (una sola vez, al inicio)

Para evitar preguntar lo mismo 3 veces, reunir al inicio del flujo todo lo que se necesita en los 3 pasos:

1. **Tipo de asignacion + numero** (Ticket `ti`/`num` o Tarea `ta`/`num`) — usado en el nombre de rama, en la segunda linea del commit, y en las `References` del commit/PR.
2. **Titulo del ticket/tarea** — usado en la segunda linea del commit (`Ticket <num>: <titulo>`).
3. **Modulo(s) afectado(s)** — derivable del diff una vez haya cambios, pero si se conoce de antemano ayuda a proponer el nombre de rama.
4. **TAG / tipo de cambio** — uno solo, coherente entre el `tipo` de la rama y el `TAG` del commit (ver tabla en `commit-message` seccion 1).
5. **Rama base (origen)** — desde donde se parte.
6. **Nombre corto en ingles** — para el nombre de rama.
7. **Resumen / Error o Contexto / Causa / Solucion** — el contenido tecnico del cambio. Puede completarse progresivamente a medida que se hacen los cambios de codigo, no hace falta tenerlo completo antes de crear la rama.
8. **Nota opcional para el commit** — preguntar, nunca asumir (ver `commit-message`).

No es necesario tener el punto 7 completo para ejecutar el paso 1 (crear rama); si el trabajo de codigo todavia no se hizo, crear la rama primero y completar el resto del flujo cuando los cambios esten listos.

## Flujo de trabajo

### Paso 1 — Rama (`branch-create`)
1. Reunir los elementos 1, 3-6 de la seccion anterior.
2. Seguir el flujo de `branch-create`: verificar rama base, construir el nombre, confirmar con el usuario, ejecutar `git checkout -b`.
3. Detenerse aqui si el usuario todavia no tiene los cambios de codigo listos — retomar el paso 2 cuando los tenga.

### Paso 2 — Commit (`commit-message`)
1. Con los cambios de codigo ya hechos y revisados, reunir los elementos 1, 2, 4, 7, 8 de la seccion anterior (lo que falte).
2. Seguir el flujo de `commit-message`: analizar `git diff`/`git status`, redactar el mensaje con el orden resumen -> error -> causa -> solucion en prosa (sin encabezados literales), mostrarlo para aprobacion.
3. Si el usuario aprueba, hacer `git add` de los archivos relevantes (nunca `git add -A`) y `git commit`.

### Paso 3 — Push + PR (`pr-create`)
1. Verificar precondiciones de `gh` (instalado + autenticado) — si falta algo, seguir las instrucciones de `pr-create` (nunca ejecutar `sudo` ni `gh auth login` por el usuario).
2. Inferir la rama base del PR (normalmente la misma rama base usada en el paso 1).
3. Construir titulo (= primera linea del commit) y cuerpo del PR con encabezados Markdown (Resumen/Problema/Causa/Solucion + References), **sin seccion de plan de pruebas**.
4. Mostrar el borrador completo para aprobacion explicita.
5. Si el usuario aprueba: `git push -u origin <rama>` seguido de `gh pr create`.
6. Devolver la URL del PR.

**Caso multi-repo (fix que toca un submodulo + su repo de cliente) — flujo detallado:**

1. **Rama en el submodulo** (checkout de desarrollo, no el submodulo embebido dentro del repo de cliente):
   - Base: **siempre, por defecto**, el **hash exacto** que el submodulo tiene desplegado/checkout en el entorno del cliente en el que se esta trabajando (origen = hash-corto, nunca un nombre de rama de mantenimiento tipo `maint-l10n-*`/`maint-*`/`rls-<proyecto>` — ver `branch-create`).
   - **Unica excepcion**: cuando el usuario pide **explicitamente, en ese momento**, enviar el cambio a la rama de mantenimiento del submodulo (ej. `maintenance-17.0`, `l10nve_17.0`) en lugar de partir del hash del cliente. Nunca asumir esta excepcion por iniciativa propia ni inferirla del contexto — solo aplica si el usuario lo pide con esas palabras.
   - Desarrollar, commitear (`commit-message`) y `git push origin <rama-submodulo>` — **siempre, inmediato**, sin excepcion, sea cual sea el `origen`.

2. **Bump en el repo del proyecto/cliente**:
   - Volver al repo principal, entrar al submodulo embebido y traer la rama recien pusheada (`git checkout -b <rama-submodulo> && git pull origin <rama-submodulo>`, o `git submodule update --init --recursive` si ya esta publicada).
   - Volver a la raiz del proyecto, `git add <submodulo>` y commitear siguiendo el caso especial de bump de puntero de submodulo (skill `commit-message`, seccion 7) — nunca redactar el mensaje desde cero.
   - Push + PR del repo principal hacia la rama staging del proyecto (flujo normal de `pr-create`).

3. **PR del submodulo — solo si va a mantenimiento**: si el cambio ya fue validado y se integra a una rama compartida entre clientes (`l10nve_17.0`, `maint-*`, etc.), crear PR del submodulo hacia esa rama. Si todavia es una prueba puntual en un solo cliente, dejar la rama del submodulo pusheada sin PR (ver `pr-create`, seccion "Submodulos: push siempre, PR solo si va a mantenimiento").

Preguntar siempre, por separado: (1) si se abre PR para el submodulo o se difiere, y (2) si se abre PR para el repo principal (normalmente si, sin condicion).

## Puntos de control (siempre pedir confirmacion explicita antes de)
- Crear la rama (`git checkout -b`)
- Crear el commit (`git commit`)
- Hacer push (`git push`)
- Crear el PR (`gh pr create`)

Estos 4 puntos son independientes entre si — aprobar uno no aprueba los siguientes.
