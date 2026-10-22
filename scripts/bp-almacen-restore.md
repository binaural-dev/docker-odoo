# Restaurar la base del almacén de Bolipuertos

Guía para sacar un respaldo de la base del almacén (`BP-RELEASE-ALMACEN`) y
montarlo en una instancia de docker-odoo con el código actual de
`bolipuertos-v18`. Hace falta, por ejemplo, el día que toque fusionar esa base
con la de producción.

Script: `scripts/bp-almacen-restore` (se corre desde la raíz de docker-odoo).

## Dónde está la base

| Dato | Valor |
|---|---|
| Servidor | `10.50.27.78` (`ccs-odoobd18-bpp`), alias ssh `almacen-bp-18` (usuario `usuario`) |
| docker-odoo | `/home/usuario/docker-odoo`, `PROJECT_NAME=bp18` |
| Contenedores | `bp18` (Odoo 18), `bp18_db` (postgres 15, usuario `odoo`) |
| Bases | `BP-RELEASE-ALMACEN` y `BP-RELEASE-CONGRESO` |
| Filestore | `/home/odoo/data/filestore/<base>` dentro de `bp18` |
| Código | `bolipuertos-v18` rama `release` del 2025-11-06 |

Ese servidor es solo lectura: el script únicamente corre `pg_dump` y `tar` ahí.
El filestore de origen está incompleto (en 2026-10 tenía 261 de 5857 archivos
referenciados, faltan sobre todo imágenes de contactos y empleados). Es así en
el servidor, no es un problema de la copia.

Para usar el alias, en `~/.ssh/config`:

```
Host almacen-bp-18
    HostName 10.50.27.78
    User usuario
```

## Uso rápido

```bash
# 1. Desde una máquina con acceso al almacén: saca dump.sql + filestore y arma el ZIP
scripts/bp-almacen-restore backup
#    -> ~/workspace/18/respaldos-almacen-bp18/<fecha>/BP-RELEASE-ALMACEN_<fecha>.zip
#    (-o DIR para otra carpeta; ALMACEN_DB=BP-RELEASE-CONGRESO para la otra base)

# 2. Si el destino es otra máquina (p. ej. la VM .76), copiar el ZIP:
rsync -a --partial -e 'ssh -p 977' BP-RELEASE-ALMACEN_<fecha>.zip binaural@10.50.27.76:/var/home/backups/

# 3. En la máquina con la instancia destino, desde la raíz de docker-odoo:
scripts/bp-almacen-restore all -i <instancia> -d <base> -z <zip>
#    ej.: scripts/bp-almacen-restore all -i bp-demo -d demo_ALMACEN_10_21_2026 -z /var/home/backups/BP-RELEASE-ALMACEN_2026-10-21.zip
```

La base destino tiene que cumplir el `db_filter` de la instancia en
`instances.json` (bp-demo: `^demo_`, bp-deploy: `^BPDEPLOY_`); el script lo valida.
Para la fusión con producción conviene restaurar primero en una instancia de
pruebas con el mismo código que tenga producción ese día.

`all` encadena estos pasos, que también se pueden correr sueltos para retomar
después de un fallo:

| Paso | Qué hace |
|---|---|
| `restore` | `./odoo restore <inst> -z <zip> -d <base> --skip-post-restore` |
| `prepare` | Parches SQL de abajo |
| `update` | `-u all` dentro del contenedor; reintenta solo si el error es de concurrencia |
| `post` | `scripts/post_restore_db --skip-module-update`: repone crons, Environment, parámetros, Sandbox, assets |
| `verify` | Módulos sin estados intermedios y `/web/login` respondiendo 200 |

Los logs del `-u all` quedan en `.tmp_ignored/bp-almacen-restore/`.

## Por qué hacen falta parches

La base viene de código de hace un año. Con `-u all` sobre el código actual,
Odoo recorre los módulos en orden de dependencias y valida cada vista contra lo
que hay en la base. Varias cosas del código solo funcionan en bases que ya
tenían datos de versiones intermedias, así que en una base vieja fallan. El paso
`prepare` corrige cada una (todos los parches son idempotentes):

1. **Crons pausados.** `--skip-post-restore` no los pausa, y el hilo de cron del
   servidor (siempre corriendo) toca la base durante el `-u all`: `deadlock
   detected` o `could not serialize access`. Se pausan en
   `_restore_paused_crons`, el mismo formato de `odoo_restore`, y
   `post_restore_db` los repone.
2. **`billing_and_collection.menu_clientes_root` → `menu_customers_root`.** El
   commit `3553960e` renombró el menú sin migración, y `tools_bp` lo usa sin tener
   `billing_and_collection` en `depends`, así que se carga antes y no lo encuentra.
3. **Acción `national_ports.action_payment_request_mass_port_origin_wizard`.**
   `retention_type` la usa en un botón, pero `national_ports` depende de
   `retention_type` (dependencia circular). Se crea una provisional con el mismo
   xmlid; al actualizarse, `national_ports` la sobrescribe.
4. **Plazos de pago `tools_bp.account_payment_term_incomes_*`.** El XML (noupdate)
   les pone `payment_condition`, campo que define `bp_port_dashboard`, que no está
   en las dependencias de `tools_bp` ni instalado en el almacén. Se crean los tres
   plazos sin ese campo y Odoo salta los registros noupdate. Si `bp_port_dashboard`
   está instalado, el parche no hace nada.
5. **Vistas obsoletas.** Vistas de módulos propios cuyo xmlid ya no existe en el
   código. Odoo las borraría al final del update, pero antes rompen la validación
   de otras vistas (p. ej. una que usaba el campo `shirt_size`, ya eliminado). Se
   desactivan.
6. **Vistas heredadas con arch viejo.** Vistas de módulos propios que siguen en el
   código pero con el contenido de 2025, que apunta a nodos o campos que cambiaron.
   Se vacían (`<data/>`) y el `-u all` las reescribe desde el XML. Las noupdate no
   se tocan.

Los defectos 2, 3 y 4 son del código de `bolipuertos-v18`. Si se corrigen allí
(declarar las dependencias, sacar el botón de `retention_type` hacia
`national_ports`, mover los plazos a un módulo que dependa de
`bp_port_dashboard`), esos parches pasan a no hacer nada.

## Si el `-u all` falla con un error nuevo

El código sigue cambiando, así que puede aparecer un caso que no está acá. El
script se detiene y muestra el módulo y el error; el log completo queda en
`.tmp_ignored/bp-almacen-restore/update_<base>_<n>.log`. Errores vistos y su
patrón:

| Error | Causa típica | Arreglo |
|---|---|---|
| `External ID not found: modulo.xmlid` | El xmlid fue renombrado, o lo define un módulo que se carga después | Renombrar en `ir_model_data` o crear un registro provisional con ese xmlid |
| `XMLID ... no válida para el botón de tipo de acción` | Igual que arriba, en un botón | Igual que arriba |
| `El campo "x" no existe en el modelo` (al validar una vista) | Una vista vieja de la base usa un campo eliminado | Ver qué vista es (`view` en el contexto del error) y desactivarla si ya no está en el código, o vaciar su arch si sigue |
| `no se puede localizar en la vista principal` | Una vista heredada espera un nodo que agregaba otra vista ya borrada | Igual que arriba |
| `Invalid field 'x' on model 'y'` (al cargar data) | Un XML de datos usa un campo de un módulo que no es dependencia y no está instalado | Precrear el registro con su xmlid si es noupdate, o instalar ese módulo si corresponde |
| `DeadlockDetected` / `SerializationFailure` | Concurrencia con el servidor | El script reintenta; si persiste, revisar que los crons estén pausados |

Después de arreglar, retomar con `scripts/bp-almacen-restore update -i ... -d ...`
(y luego `post` y `verify`). No hace falta restaurar de nuevo: un `-u all` fallido
hace rollback y la base queda como estaba.

Si el arreglo es general, agregarlo al paso `prepare` del script para que la
próxima vez salga solo.

## Historial

- 2026-10-21: primera restauración. Se montó en bp-deploy local
  (`BPDEPLOY_ALMACEN_10_21_2026`) y en bp-demo de la VM .76
  (`demo_ALMACEN_10_21_2026`), con los parches de arriba.
