# AI_LOG — fleet_inspection (Ejercicio 2)

## Herramientas
- Claude Code (app de escritorio), modelo Claude Opus 5.5.

## Prompts clave
1. «Arranca el ejercicio 2-A: rama nueva, mueve fleet_inspection a la carpeta de addons y migra a Odoo 18.»
   - Leyó el módulo completo y, antes de editar, revisó en el código fuente de Odoo 18 del contenedor cada
     referencia que usa el módulo: campos de `ir.cron`, export de `Form`, advertencia de `create` por lotes,
     `t-esc`, menús y categoría de `fleet`. Así la tabla de cambios se basa en lo que dice Odoo 18 y no en
     memoria.
2. Contraprueba: «instala el código de 16 sin migrar para ver qué advertencias da».
   - Con `git stash` instaló el código original. Obtuvo las advertencias de `states` y `create`, el
     `Invalid field 'numbercall'` y, en una segunda corrida, `Invalid view type: 'tree'`. Esto demuestra que
     el registro de la versión migrada (sin advertencias) es una verificación real.

3. «Sigue con el 2-B: catálogo de tipo de vehículo y script de migración.»
   - Antes de cambiar el código, preparó la base del escenario real (versión del tramo A con 26
     inspecciones) para poder actualizarla después con `-u`. Separó la lógica en `migration_utils.py` para
     probarla, y respaldó la selección en una columna propia porque Odoo borra la columna del campo
     eliminado al terminar la actualización.

## Lo que la IA hizo mal
- Asumió que la categoría `base.module_category_human_resources_fleet` estaba en los datos de `base`. Al
  buscarla no apareció ahí; resultó que la genera la categoría del módulo `fleet`, y `fleet` mismo la usa. No
  hubo que cambiar nada, pero el supuesto inicial era incorrecto y se detectó al verificar.
- La primera contraprueba se detuvo en el cron y no llegó a las vistas. Hubo que repetirla quitando solo
  `numbercall` y `doall` para tener evidencia del error de `<tree>`.

- En la actualización real aparecieron avisos `<string>:19: (WARNING/2)` y `Undefined substitution
  referenced: "---"`. No eran de la migración: Odoo interpreta el README.md como reStructuredText para la
  descripción del módulo, y las tablas Markdown le parecen sustituciones. Se resolvió con una `description`
  corta en el manifiesto. Lo mismo pasaba desde antes en `sale_commission`, que no se tocó por ser el módulo
  del hotfix.

- **Tramo C, lotes que no escalaban:** la primera versión por lotes buscaba en cada lote las filas pendientes
  desde el principio de la tabla. Con 10.000 parecía bien, pero con 100.000 tardó 15 veces más en lugar de
  10. Se detectó porque se midió con dos volúmenes, y se cambió a paginación por id.
- **Primer borrador de MIGRATION_PLAN.md con un paso que no funcionaba:** detenía la instancia
  (`./odoo stop`) antes de `./odoo update`, pero ese comando corre Odoo dentro del contenedor de la instancia.
  Se detectó al leer `docs/comandos-odoo.md`, y el plan ahora cierra el acceso deteniendo el proxy. También
  afirmaba que al revertir Odoo borraba la tabla del catálogo: el ensayo de la reversión mostró que la tabla
  queda (Odoo no borra tablas de modelos eliminados).

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)
