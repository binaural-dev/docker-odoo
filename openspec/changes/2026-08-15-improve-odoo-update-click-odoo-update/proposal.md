# Mejorar `./odoo update`: sin `-m` no lista módulos, `click-odoo-update` por defecto

**Estado: implementado y verificado (2026-08-15).**

## Por qué

Dos problemas en el subcomando `update`:
1. Sin `-m`, `prompt_for_modules()` siempre desplegaba una lista interactiva
   de todos los módulos custom detectados para elegir uno o más — en vez de
   simplemente actualizar todo sin preguntar.
2. Cuando el destino era "todos los módulos", `bash_update_modules()` corría
   `odoo -u all` directo, que reprocesa literalmente cada módulo instalado,
   haya cambiado o no — mucho más lento de lo necesario.

Al investigar la solución se encontró que `click-odoo-update` (la herramienta
que resuelve exactamente el problema 2: solo actualiza addons cuyo hash de
archivo cambió desde la última actualización) **no estaba instalada en
ninguna imagen**, a pesar de que `.resources/entrypoint.d/700-fix-dbs` ya la
invoca cuando se activa `FIXDBS=true` en el arranque automático. Ese camino
estaba roto en la práctica (habría fallado con "command not found" si alguna
vez se hubiera activado).

## Qué cambia

- `.resources/Dockerfile.template`: se agrega `click-odoo-contrib` a la lista
  de paquetes pip instalados — esto además destraba el uso ya existente (pero
  roto) en `700-fix-dbs`, sin tocar ese archivo.
- `bash_update_modules()`: cuando el destino es `"all"`, usa
  `click-odoo-update --if-exists -d <dbname>` en vez de `odoo -u all`. Con el
  nuevo flag `-f`/`--force`, agrega `--update-all` (flag nativo de
  `click-odoo-update` para forzar un upgrade completo) — así que tanto el
  camino inteligente como el forzado pasan por la misma herramienta, sin caer
  de vuelta a invocar `odoo` directo para el caso forzado.
- Actualizar un módulo específico vía `-m <modulo>` no se ve afectado — sigue
  siendo `odoo -u <modulo>` directo, ya es una operación puntual y deliberada.
- El handler de `update` ya no llama a `prompt_for_modules()` cuando `-m` no
  se pasa — pasa directo a `"all"`. `prompt_for_modules()` quedó sin
  llamadores en ningún lado y se eliminó (no se dejó código muerto).

## Impacto

- Validado: `click-odoo-update --help` (dentro de la imagen reconstruida)
  confirma los flags usados (`-d`/`--database`, `--if-exists`,
  `--update-all`).
- Build de prueba (`docker compose build odoo-integra-17.0`) confirmó que
  `click-odoo-update` queda disponible en el PATH del contenedor tras el
  cambio al Dockerfile.
- `python3 odoo update --help` confirma el nuevo flag `-f`/`--force` en el
  parser.
- `get_custom_modules()` (usada también por `prompt_for_test_modules` para el
  comando `test`, un caso distinto donde sí tiene sentido elegir módulos
  explícitamente) no se tocó — solo se eliminó `prompt_for_modules`, que
  quedó exclusivamente sin uso.
