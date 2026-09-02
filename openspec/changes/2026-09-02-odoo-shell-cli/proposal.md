# Shell operativo de Odoo: `./odoo shell`

**Estado: implementado y verificado (2026-09-02).**

## Por qué

Para operar el ORM de una instancia (buscar, leer, crear, escribir, llamar un
método) hoy había que entrar al contenedor y armar un script ad-hoc, o usar
`odoo shell` a mano dentro del contenedor. El usuario quería un CLI one-shot
con el patrón de siempre del launcher (elegir instancia, luego subcomando),
que además resolviera dos limitaciones que encontró al probar la WebExtension
OdooTerminal (en la que se inspiró):

1. OdooTerminal vive en el navegador y habla JSON-RPC: sus métodos privados
   (`_prefijados`) están bloqueados por el servidor — no es un problema del
   comando `call`, es inherente a ser WebExtension.
2. No tiene shell interactivo ni una forma clara de "ejecutar en todos los
   registros".

Al investigar alternativas existentes (click-odoo, el paquete odoo-shell,
wrappers de la comunidad) no se encontró ningún CLI ready-made con la
gramática `search/read/method` pedida. En cambio, `click-odoo` (LGPL-3, de
ACSONE) **ya está instalado dentro de las imágenes** (es dependencia de
`click-odoo-contrib`, presente en 14.0 y 19.0) y resuelve el problema de
fondo: correr código Python en un `env` inicializado, por stdin, con rollback
opcional. La decisión fue construir un wrapper delgado sobre `click-odoo`, no
portar OdooTerminal completo (que es un intérprete con loops/funciones/
alias/recordsets — scope grande e innecesario).

## Qué cambia

- `scripts/odoo-shell` (nuevo, Python + argparse, standalone): recibe
  `--container`, `-d/--db`, `--user`, `--no-commit` (→ `--rollback`),
  `--json`. Subcomandos: `shell` (REPL ipython interactivo), `search`,
  `read`/`browse`, `count`, `create`, `write`, `unlink` (con `--yes`),
  `method`. Genera un snippet Python y lo inyecta por stdin a
  `docker exec -i <container> click-odoo -d <db> --log-level=error
  [--rollback] --no-interactive`. Parsea `--domain`/`--values`/`-a`/`-k`
  como literales Python seguros (`ast.literal_eval`); `-k` también acepta
  `clave:valor,clave2:valor2`. Salida JSON pretty (compacta con `--json`).
  `method` usa `getattr(recs, name)(*args, **kwargs)` — métodos privados OK;
  con `--ids` hace `browse`, sin ids hace `search` (sin limit = todos).
- Launcher `odoo`: subparser `shell` (instancia posicional opcional, `-d`,
  `--user`, resto por `argparse.REMAINDER`, patrón del comando `apk`). En el
  dispatch: si el posicional no es una instancia conocida se re-clasifica
  como subcomando y se pide la instancia; se extrae `-d <db>` del REMAINDER
  para no volver a preguntar la base; `prompt_for_database` respeta el
  `db_filter` de la instancia. `shell` se agregó a `actions_with_instance`.
- `openspec/specs/odoo-cli-tooling/spec.md`: requirement "Shell operativo de
  Odoo contra una instancia" con sus escenarios.
- `readme.md`: fila en la tabla de comandos y sección con un ejemplo por
  subcomando.

## Impacto

- Verificado en vivo contra `odoo-binaural` (Odoo 19.0): `search` con dominio/
  campos/límite/orden; `read`/`browse`; `count`; `create`/`write` con
  `--no-commit` (rollback real); `method -n _compute_display_name --ids 1,3`
  (método privado, corre y no retorna → `null`, que es correcto para un
  compute); `method -n search -a "[[...]]" -k "{'limit':2}"` (recordset
  normalizado a ids); `unlink` sin `--yes` aborta. El parsing de `-k` se
  confirmó porque el TypeError de `_compute_display_name` con kwargs ajenos
  demuestra que los kwargs llegan de verdad al método.
- `--no-commit` se traduce a `--rollback` de click-odoo: probado que un
  `create` con rollback no deja registro (el id devuelto es "transaccional").
- El REPL interactivo no se probó en CI (requiere TTY) pero usa la ruta
  estándar `docker exec -it ... click-odoo --shell-interface ipython`.
- Las operaciones de escritura confirman el commit de click-odoo (por defecto
  persiste); `--no-commit` revierte.