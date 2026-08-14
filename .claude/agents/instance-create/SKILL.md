---
name: instance-create
description: Crea una nueva instancia de Odoo en instances.json siguiendo el patron del proyecto (deteccion de version de Odoo via manifests, submodulos disponibles del cliente, y puerto externo libre). Usar cuando el usuario pida dar de alta un proyecto/cliente nuevo o agregar una instancia a instances.json.
---

# instance-create

Da de alta una instancia nueva en `instances.json` (raiz del repo `docker-odoo`, no versionado). Automatiza el paso "agregar entrada en `instances`" del FAQ del `readme.md` ("Como agrego un nuevo proyecto/instancia?"), detectando por el usuario lo que se puede derivar del filesystem en vez de pedirlo a ciegas.

No reemplaza `./odoo build && ./odoo start` como forma de levantar la instancia: `./odoo build` se ejecuta como parte de este mismo flujo (ver seccion "Flujo de trabajo", paso 9) porque es lo que hace que la instancia nueva quede reconocida por el resto de comandos `./odoo`; `./odoo start <nombre>` queda aparte, como paso manual posterior.

## Informacion necesaria

1. **Nombre de la instancia** — *preguntar si no es evidente*. Debe existir ya como carpeta en `src/custom/<nombre>`. Si no existe, avisar y detenerse: clonar el repo del cliente no es parte de esta skill.
2. **Version de Odoo** (`odoo_version`) — *derivable*: leer el campo `"version"` de los `__manifest__.py` de los modulos dentro de `src/custom/<nombre>/` y tomar el prefijo `MAYOR.MENOR` (ej. modulos con `"17.0.1.0.3"` -> `odoo_version: "17.0"`). Si los manifests no coinciden entre si, o no hay modulos con manifest, preguntar al usuario en vez de asumir.
3. **Submodulos disponibles** — *derivable*: listar `src/custom/<nombre>/` y comprobar cuales de `integra-addons`, `odoo-venezuela`, `third-party-addons` existen como carpeta real. No todos los clientes tienen los 3 — nunca asumir que estan todos.
4. **`external_port`** — *derivable*: leer todos los `external_port` ya usados en `instances.json` y elegir cualquier entero libre que no colisione con ninguno de ellos. No hace falta que sea el siguiente numero secuencial ni evitar huecos existentes en la numeracion (ej. si hay un hueco entre dos puertos usados, usarlo ahi es valido) — la unica regla real es que no se repita.
5. **`db_filter`** — *preguntar solo si hay riesgo de colision* (nombre de base de datos parecido al de otra instancia ya existente). Por defecto se omite (la mayoria de instancias no lo usan).
6. **`database` / `odoo_config`** — *derivable*: usar `"pg16"` y `"_default"` salvo que el usuario pida explicitamente otra cosa (hoy son las unicas claves definidas en `instances.json`).

## Flujo de trabajo

1. Leer `instances.json` completo y confirmar que el nombre de instancia no exista ya en `instances.instances`.
2. Verificar que `src/custom/<nombre>` existe; listar su contenido para detectar submodulos (`integra-addons`, `odoo-venezuela`, `third-party-addons`).
3. Derivar `odoo_version`:
   ```bash
   grep -h '"version"' src/custom/<nombre>/*/__manifest__.py
   ```
   Tomar el prefijo `MAYOR.MENOR` comun a todos. Si no hay consenso, preguntar.
4. Elegir un `external_port` libre comparando contra todos los `external_port` de `instances.json` (cualquier entero no usado sirve, no necesariamente el siguiente en la secuencia).
5. Armar el bloque `addons` en este orden fijo, incluyendo solo lo que exista de verdad:
   1. `src/enterprise-<odoo_version>`
   2. `src/custom/<nombre>`
   3. `src/custom/<nombre>/integra-addons` (si existe)
   4. `src/custom/<nombre>/odoo-venezuela` (si existe)
   5. `src/custom/<nombre>/third-party-addons` (si existe)
6. Mostrar al usuario el bloque JSON propuesto completo (`odoo_version`, `external_port`, `database`, `odoo_config`, `overwrite_odoo_config.addons`, y `db_filter` si aplica) para su **aprobacion explicita antes de escribirlo**.
7. Si aprueba, insertar la entrada dentro de `instances.instances` usando Edit (no reescribir todo el archivo), respetando el estilo de comas/formato ya presente en el JSON.
8. Validar el resultado:
   ```bash
   python3 -c "import json; json.load(open('instances.json'))"
   ```
   y confirmar que el `external_port` elegido sigue sin repetirse entre instancias.
9. Ejecutar `./odoo build` inmediatamente despues de escribir la entrada, sin pedir confirmacion aparte — regenera `docker-compose.generated.yml` y la config de nginx incluyendo el servicio de la instancia nueva, y es lo que la hace reconocible por el resto de comandos `./odoo` (`start`, `bash`, `logs`, `psql`, etc.). Mostrar la salida al usuario y revisar que no haya errores.
10. Recordar al usuario que `./odoo start <nombre>` sigue siendo un paso manual aparte para levantar el contenedor.

## Puntos de control

- **Siempre pedir confirmacion explicita antes de** escribir la entrada nueva en `instances.json`.
- `./odoo build` se ejecuta automaticamente justo despues de escribir la entrada (no requiere una segunda confirmacion) porque es necesario para que la instancia quede operativa via CLI.
- `./odoo start` **no** se ejecuta automaticamente — queda como paso manual que el usuario decide cuando hacer.
