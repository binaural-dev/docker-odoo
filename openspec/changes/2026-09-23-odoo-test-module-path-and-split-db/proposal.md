# `./odoo test` / `scripts/odoo-test`: `-m` acepta path/`all`, y `--per-module-db` para DB independiente por módulo

**Estado: implementado y verificado (2026-09-23).**

## Por qué

Al testear varios módulos custom a la vez, dos limitaciones repetidas:

1. `-m`/el posicional solo aceptaba nombres de módulo sueltos. Para testear
   "todos los módulos de esta carpeta" o "todos los módulos custom de la
   instancia" había que enumerarlos a mano, uno por uno.
2. Al pasar varios módulos, todos se instalaban y testeaban juntos en una
   sola base de datos, con un solo reporte combinado. Para CI (o para saber
   con precisión qué módulo específico rompió, sin que el ruido de uno
   tape el resultado de otro) hace falta que cada módulo corra aislado, en
   su propia base, con su propio veredicto.

## Qué cambia

- **`scripts/odoo-test`**: `-m`/el posicional acepta, por token separado
  por coma, ademas de un nombre de módulo:
  - un **path DENTRO del contenedor** (contiene `/`): debe estar dentro de
    alguno de los `--addons` (igual o anidado) — se expande a todos los
    módulos que haya ahí dentro (`resolve_requested_modules`).
  - `all`: se expande a TODOS los módulos escaneados en TODOS los `--addons`.
- **`--per-module-db`** (nuevo flag): cada módulo de la lista ya resuelta
  corre en su **propia base de datos independiente**, secuencialmente (una
  instalación, una corrida de tests, una medición de cobertura por módulo),
  en vez de todos juntos en una sola base (comportamiento por defecto, sin
  cambios). Con `--recursive`, el árbol de dependencias se calcula **por
  módulo** (no combinado): un módulo compartido entre varios de los
  indicados se instala y testea más de una vez, una por cada base
  independiente — trade-off deliberado a favor de un veredicto limpio y
  atribuible por módulo. La confirmación de `--recursive` se hace **una
  sola vez**, mostrando los N árboles juntos antes de arrancar el loop
  completo (no N pausas intercaladas). No es compatible con `-d`/`--db`
  explícito (cada módulo autogenera su propio nombre de base).
- **Reportes en modo `--per-module-db`**:
  - `--out-coverage-json`/`--out-logs`: un subarchivo por módulo dentro del
    directorio dado (`<dir>/<modulo>/coverage.json`,
    `<dir>/<modulo>/test_run.log`) — con más de un módulo, un solo archivo
    pisaría el de los demás.
  - `--out-json`: JSON combinado, recortado, un módulo por key —
    `{modulo: {at_install, post_install, totals, verdict: {passed}}}`.
  - **`--out-summary-json`** (nuevo flag, solo válido junto con
    `--per-module-db`): JSON ultra-resumido, un módulo por key —
    `{modulo: {passed, coverage}}`.
- **`./odoo`**: los subcomandos `test` reciben y reenvían los flags nuevos
  (`--per-module-db`, `--out-summary-json`) tal cual a
  `scripts/odoo-test`, sin lógica propia (mismo patrón que el resto de
  flags de `test`). Además:
  - `-m`/el posicional de `./odoo test` traduce un path del **host**
    (relativo al repo, o absoluto dentro de él) al equivalente dentro del
    contenedor (`/home/odoo/<mismo relativo>`) antes de reenviarlo —
    `scripts/odoo-test` valida paths contra `--addons`, que ya vienen en
    forma de contenedor.
  - se agregó el forwarding de `--no-confirm` a `scripts/odoo-test`, que
    faltaba (gap preexistente, necesario para poder usar `--recursive` +
    `--per-module-db` sin quedar bloqueado en un prompt interactivo desde
    automatización/CI).

## Fuera de alcance, deliberadamente

- No se resuelve el orden/paralelismo de las corridas por módulo:
  `--per-module-db` corre siempre secuencial (una corrida de `coverage`
  concurrente sin `COVERAGE_FILE`/cwd separado por proceso pisaría datos de
  cobertura entre corridas).
- No se toca el shape de salida del modo normal (sin `--per-module-db`):
  `--out-json` sigue exportando el formato completo existente (con
  `modules`/`verdict` con `fail_reasons`/`not_installed_modules`).

## Verificado en runtime

Corrida real contra la instancia `integra19` (`./odoo test integra19 -m
binaural_alternate_product_name,binaural_approvals_purchase
--per-module-db --out-json ... --out-summary-json ...`): dos módulos, cada
uno en su propia base descartable (creada y borrada independientemente),
JSON combinado y resumido con el shape exacto esperado, ambos veredictos
`passed: true`. También verificado por separado (dry-run): resolución de un
path exacto a un módulo, `all` acotado a un `--addons` root expandiendo a
sus ~49 módulos, y traducción de path host-relativo a path de contenedor
desde `./odoo test`.

**Incidente aparte, no relacionado con este cambio:** al usar `integra19`
para esta verificación se detectó que esa instancia nunca había sido
aprovisionada con su rol dedicado de Postgres (única instancia en
`instances.json` cuyo `db_user` no sigue la convención `odoo_<instancia>`
del resto), lo que dejaba su `WorkerCron` en loop de
`permission denied for table ir_module_module` apenas se la usaba de
verdad. Se aprovisionó el rol (`./odoo provision-role integra19`) y se
otorgó `GRANT odoo_integra19 TO integra19` para heredar el acceso a las
tablas ya existentes (propiedad del rol legado `odoo_integra19`). Queda
pendiente, fuera de este cambio, decidir si conviene alinear
`instances.json` a la convención `odoo_integra19` en vez de `integra19`.
