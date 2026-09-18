# `./odoo test` / `scripts/odoo-test`: usar `-u` cuando la base ya existe y el módulo ya está instalado

**Estado: implementado y verificado (2026-09-04).**

## Por qué

Al escribir una suite de tests de sincronización real (sin mocks) para
`binaural_integration_o`/`binaural_integration_h` (repo `integra-addons`,
fuera de este proyecto), esos tests necesitan correr contra las bases reales
ya restauradas (`integra_sync_operativo`/`integra_sync_homologado`), no
contra una base descartable nueva: dependen de `res.company.api_url`/
`api_key`/`jwt_secret` ya configurados entre los dos ambientes y de un plan
de cuentas/partners/productos ya sincronizados que una base vacía no tiene.

Al correr `./odoo test -i integra-sync-operativo -m binaural_integration_o -d
integra_sync_operativo --no-rm-db`, el resumen daba `Tests ejecutados: 0`,
`Fallos: 0`, `Errores: 0`, `Resultado: ✅ OK` — sin ninguna pista de que algo
estuviera mal. Causa raíz: `scripts/odoo-test` arma el comando de Odoo con
`-i {modulos}` siempre, sin importar si la base ya existe. `-i` (install) es
un no-op para Odoo si el módulo ya está instalado: no reinstala, no recarga
el código Python, y por lo tanto tampoco redescubre los archivos nuevos en
`tests/`. El script sí detecta y reutiliza una base existente (`db_exists()`
antes de `create_db()`), pero seguía pidiéndole a Odoo que "instale" un
módulo que ya estaba instalado.

## Qué cambia

- `scripts/odoo-test`: antes de armar `odoo_cmd`, si la base (`-d`) ya existe
  y **todos** los módulos pedidos (`modules_str`) figuran `state =
  'installed'` en `ir_module_module` de esa base (vía la función ya existente
  `query_module_states`, reutilizada — antes solo se llamaba después de
  correr, para el resumen), se usa `-u` en vez de `-i`. Se imprime un aviso
  explícito (`→ '<modulos>' ya esta instalado en '<base>': usando -u...`)
  para que no vuelva a pasar desapercibido. Si la base es nueva o falta
  instalar algo, el comportamiento no cambia (`-i`, flujo normal de base
  descartable).

**Fuera de alcance, deliberadamente:**

- No se tocó el default de `--tags` (`'all'` → `/modulo1,/modulo2,...`).
  Ese filtro exige implícitamente el tag `'standard'` (comportamiento de
  `odoo/tests/tag_selector.py`, no de este script), lo que excluye tests que
  se taguean a propósito con `-standard` (como la suite de sync mencionada
  arriba, que necesita hacer HTTP real sin que Odoo la bloquee). Cambiar el
  default afectaría a todos los usos existentes de este script para
  cualquier módulo, no solo a este caso puntual — se documentó como
  workaround (agregar el tag extra a mano en `--tags`) en vez de tocar el
  comportamiento general.

## Impact

- **Archivo:** `scripts/odoo-test` (standalone, sin versión de módulo que
  bumpear).
- **Compatibilidad:** ningún cambio de comportamiento para el flujo normal
  (base nueva/descartable, el 99% de los usos actuales). Solo cambia cuando
  `-d` apunta explícitamente a una base ya provisionada con el módulo ya
  instalado — antes silenciosamente no hacía nada, ahora corre los tests de
  verdad.
- **Verificado en runtime:** reproducido el bug exacto con el comando real
  del usuario contra `integra_sync_operativo` (`Tests ejecutados: 0`, sin
  errores), aplicado el fix, y confirmado que el mismo comando ahora imprime
  el aviso de `-u` y corre los tests (`Tests ejecutados: 5`, `0 Fallos`, `0
  Errores`).

**References:** Suite de tests de sincronización de `binaural_integration_o`/
`binaural_integration_h` (repo `integra-addons`, fuera de este proyecto) —
motivó el hallazgo pero vive en otro repositorio.
