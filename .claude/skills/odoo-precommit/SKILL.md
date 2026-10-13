---
name: odoo-precommit
description: Diagnostica y corrige fallos del pre-commit/pylint-odoo (OCA) en módulos de multi-docker-odoo usando scripts/precommit. Úsala cuando el usuario mencione precommit, pre-commit, pylint_odoo, códigos como W8301/E8103/C8107, "Check for Odoo modules using pylint", oca-checks-po, o pida arreglar el pipeline/CI de un PR de Odoo.
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion
---

## Cuándo usar

- El usuario pide arreglar errores de `pre-commit` o del CI/pipeline de un PR de Odoo.
- Aparecen códigos tipo `W8301`, `E8103`, `C8107`, `C8108`, `W8110`, `W0404`, `W8138`.
- El usuario menciona `scripts/precommit`, `pylint_odoo`, `oca-checks-po`.

## Comando (siempre, nunca `pre-commit run --all-files` directo)

Desde la raíz de `/home/binaural80/multi-docker-odoo` (el script resuelve su propio `BASE_PATH`, pero se invoca por convención desde ahí; **nunca** parado dentro de la carpeta del addon):

```bash
python3 scripts/precommit <instancia> -m <modulo1>,<modulo2>
python3 scripts/precommit <instancia> -m all   # todos los módulos de la instancia
```

- `<instancia>` es un nombre de `instances.json` (usar `docker ps --filter "name=odoo"` o leer `instances.json` si no se sabe cuál).
- Si se omite `<instancia>`, el script pregunta interactivamente — mejor pasarla siempre explícita en uso no interactivo.
- El script clona/actualiza `precommit-config-files` (rama según `odoo_version` de la instancia) en `.ignore/` e instala `pre-commit` si falta — la primera corrida tarda más.

## Cómo leer la salida

Hay **3 hooks**; solo uno es bloqueante:

| Hook | ¿Bloquea? |
|---|---|
| `Checks for .po[t] files` | Sí — duplicados de `msgid` en `.po` |
| `pylint with optional checks` | **No** — informativo, ignorar (incluye `W8113`, `C8112`) |
| `Check for Odoo modules using pylint` | **Sí (mandatory)** — arreglar todo lo que aparezca aquí |

Formato de cada hallazgo: `archivo:línea: [CÓDIGO(severidad), Clase.método] mensaje`. Trabajar **solo** sobre lo que repite el hook mandatory (aparece dos veces en el log: una vez en el resumen "optional checks" y otra en "Check for Odoo modules using pylint" — ese segundo bloque es el que cuenta).

## Códigos más comunes y su fix

| Código | Problema | Fix |
|---|---|---|
| `E8103` | SQL injection | Usar `psycopg2.sql.SQL`/`Identifier`, o `# pylint: disable=sql-injection` si es código seguro conocido |
| `E8106` | `requests.*` sin `timeout` | Agregar `timeout=<segundos>` a la llamada |
| `W8301` | Traducción no lazy (`_() % x`) | Pasar los args como argumentos de `_()`, no con `%`/`.format()` |
| `W8303` | f-string dentro de `_()` | Igual que W8301: usar args lazy, no f-string |
| `W8138` | `except:` vacío | Loggear algo en el except, aunque sea `_logger.debug(...)` |
| `W8110` | Falta `return` en método que llama `super()` | Agregar `return super().metodo(...)` |
| `W0404` | Import duplicado | Eliminar el import repetido |
| `W0101` | Código muerto tras `return` | Eliminar el código inalcanzable |
| `C8107` | Falta `_()` en string traducible | Envolver el string en `_()` |
| `C8108` | Método `@api.depends` mal nombrado | Renombrar a `_compute_<algo>` |
| `W8113` / `C8112` | `string=` redundante / falta README.rst | **Ignorar** — solo salen en el hook opcional |

Ver [assets/fix-examples.md](assets/fix-examples.md) para el snippet mal/bien de cada uno.

## Flujo obligatorio

1. Ejecutar `python3 scripts/precommit <instancia> -m <modulo>`.
2. Si falla, mirar **solo** el bloque `Check for Odoo modules using pylint`.
3. Arreglar **un** error (o un grupo del mismo tipo en el mismo archivo).
4. Re-ejecutar el mismo comando — no acumular varios fixes sin confirmar.
5. Repetir hasta que los 3 hooks digan `Passed` (exit code 0).
6. Recién ahí, sugerir hacer commit o pasar a `/odoo-test-coverage`.

Si son varios módulos, corregir de a uno hasta que quede verde antes de correr `all`.

## Anti-patrones

- Ejecutar `pre-commit run --all-files` en vez de `scripts/precommit`.
- Pararse dentro de la carpeta del addon en vez de la raíz del repo.
- Arreglar `W8113`/`C8112` (son del hook opcional, no bloquean).
- Tocar módulos fuera de los pasados en `-m`.
- Hacer varios fixes sin volver a correr el comando entre medio.
