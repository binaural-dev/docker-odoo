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

## Lo que la IA hizo mal
- Asumió que la categoría `base.module_category_human_resources_fleet` estaba en los datos de `base`. Al
  buscarla no apareció ahí; resultó que la genera la categoría del módulo `fleet`, y `fleet` mismo la usa. No
  hubo que cambiar nada, pero el supuesto inicial era incorrecto y se detectó al verificar.
- La primera contraprueba se detuvo en el cron y no llegó a las vistas. Hubo que repetirla quitando solo
  `numbercall` y `doall` para tener evidencia del error de `<tree>`.

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)
