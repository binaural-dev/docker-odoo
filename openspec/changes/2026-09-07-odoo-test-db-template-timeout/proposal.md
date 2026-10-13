# `odoo-test`: plantilla de base de datos y corte por tiempo

**Estado: implementado y verificado (2026-09-07).**

## Por qué

Para medir la cobertura de **todos** los módulos de un repo hay que correr
`odoo-test` una vez por módulo, cada una en su propia base. Dos cosas lo hacían
impracticable a esa escala:

1. **Cada corrida instalaba la base desde cero.** `create_db()` hacía
   `createdb <db>` pelado, así que Odoo tenía que instalar `base`, `web`,
   `mail`, `account`, etc. antes de llegar al módulo. Medido sobre
   `binaural_account_asset` en un contenedor real: 73 s desde cero contra 25 s
   clonando una plantilla ya horneada — y la diferencia crece con el peso del
   árbol de dependencias del módulo. Multiplicado por cientos de módulos, es la
   diferencia entre un barrido de horas y uno de días.

2. **No había timeout.** `run_and_capture()` hacía `subprocess.Popen` sin
   límite, así que una suite trabada colgaba el barrido completo, sin
   diagnóstico y sin liberar la base.

## Qué cambia

Dos flags **aditivos** (por defecto apagados: sin ellos el comportamiento es
idéntico al anterior, verificado diffeando la salida de `--dry-run` antes y
después) y una línea de exportación.

### `--db-template <base>`

`create_db()` acepta `template` y hace `createdb -T <plantilla> <db>`.

- La plantilla debe estar horneada con la **misma versión de Odoo** que el
  contenedor: el esquema no es compatible entre versiones.
- `-i <modulo>` **no cambia**. Contra una plantilla que ya trae esos módulos
  instalados sigue siendo correcto: leyendo el fuente real de Odoo en los dos
  contenedores (`odoo/modules/loading.py:444` en 17.0, `:427` en 19.0),
  `Module.update_list()` corre siempre que se pasa `-i`, y la instalación es
  `search([('state','=','uninstalled'), ...]).button_install()` — lo ya
  instalado se saltea y la lista de módulos se refresca primero. **No hace falta
  `-u`**, y agregar `-u base` costaría 2-4 min por corrida actualizando todo el
  core.
- **El filestore se copia junto con la base.** `createdb -T` no lo clona, y los
  `ir_attachment.store_fname` del clon apuntarían a archivos que no existen. Se
  copia con `cp -a` (4-53 MB medidos) y se borra junto con la base.
- La plantilla conviene blindarla con `IS_TEMPLATE true` +
  `ALLOW_CONNECTIONS false`: con `datallowconn=false` sigue sirviendo como
  origen de `CREATE DATABASE` (es el estado de `template0`) pero deja de poder
  abrirse, así que nadie la modifica y el error "is being accessed by other
  users" se vuelve inalcanzable. Queda además un reintento (3 × 5 s) que ante
  ese error corta las sesiones **acotado a la plantilla**.

### `--timeout <segundos>`

El corte lo hace el `timeout` de coreutils **dentro del contenedor**,
prefijando solo el `coverage run`. Esto es deliberado y es el punto no obvio:
**matar el cliente de `docker exec` desde el host no mata el proceso de
adentro.** Prefijando solo ese sub-comando, `coverage report -m` y
`coverage json` corren igual después del corte, así que la cobertura parcial no
se pierde, y el exit code 124 identifica al timeout sin ambigüedad
(`compute_verdict` lo reporta como `fail_reason: "timeout"`, distinto de un
`process_exit_nonzero` cualquiera).

`run_and_capture()` queda con un reloj propio como último recurso (el del
contenedor más un margen), que drena stdout en un hilo y, si se vence, mata el
proceso de adentro con `pkill -f "<db_name>"`. El `db_name` es un token único
que aparece en la cadena de bash y en el argv de Odoo, así que el match no se
lleva puesto ni el Odoo principal del contenedor ni corridas paralelas.

### `--out-coverage-json-raw <ruta>`

Un segundo reporte de cobertura en JSON, generado con un rcfile propio que
mantiene `branch = True` pero **no** trae sección `[report]`, así que no aplica
el `omit`: incluye una entrada por cada archivo medido, `tests/` y
`__init__.py` inclusive.

Por qué hace falta: el `omit` vive en `[report]`, o sea que actúa al generar el
reporte, no al recolectar. Con el JSON sin filtrar, un consumidor puede derivar
—de **una sola corrida**— tanto la cobertura del código de producción como la
que incluye los archivos de test, sumando por archivo y aplicando la fórmula de
`coverage.py` con ramas: `(líneas ejecutadas + ramas ejecutadas) / (líneas +
ramas)`. Verificado sobre `binaural_rate`: la derivación da exactamente
`pct=42, stmts=75, miss=36`, idéntico a lo que reporta `coverage` aplicando el
`omit`, mientras el total sin filtrar da `pct=63, stmts=133, miss=38`.

Sin esto, tener las dos cifras exigiría medir dos veces cada módulo.
`--out-coverage-json` no cambia: sigue entregando el reporte con el `omit`
aplicado.

### `module_states` en `--out-json`

`query_module_states()` ya consultaba `ir_module_module.state` antes de borrar
la base, pero el dato no se exportaba: solo salía derivado dentro de
`modules.not_installed`. Ahora el `--out-json` incluye `module_states` crudo y
`exit_code`.

Con eso, un consumidor puede distinguir "no tiene tests" de "no instala" con la
información de **la misma corrida**, sin tener que reinstalar el módulo por
separado en una segunda pasada.

### Launcher

`./odoo test` reenvía `--db-template`, `--timeout` y `--no-confirm` (este
último existía en `odoo-test` pero el launcher nunca lo pasaba, así que
`--recursive` desde `./odoo test` no se podía automatizar).

## Impacto

Verificado contra los contenedores reales:

- **La plantilla no contamina la medición**: `binaural_account_asset` da
  `pct=53, stmts=30, miss=11` idéntico con y sin plantilla, en 25 s contra 73 s.
- **El timeout corta y limpia**: con `--timeout 45` sobre `binaural_unidigital`
  (suite de ~24 min), la corrida termina en 51 s con exit code 124,
  `fail_reasons: ["timeout"]`, la cobertura parcial reportada, y ni base ni
  filestore quedan colgados.
- **Sin los flags nuevos, nada cambia**: la salida de `--dry-run` antes y
  después del cambio es idéntica salvo los puertos, que ya eran aleatorios.
