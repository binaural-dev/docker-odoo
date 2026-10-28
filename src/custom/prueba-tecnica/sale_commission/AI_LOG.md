# AI_LOG — sale_commission (Ejercicio 3, ticket T-200)

## Herramientas
- Claude Code (app de escritorio), modelo Claude Opus 5.5.

## Prompts clave
1. «Arranca el ejercicio 3 en la rama hotfix/T-200: reproduce el error con un usuario vendedor y busca la
   causa raíz.»
   - Leyó el módulo y el diff `ad51040..3f4d73f`, y señaló el permiso faltante sobre `sale.commission.rule`
     y la prueba que dejó de usar `with_user()`. Primero escribió las pruebas como vendedor, las corrió y vio
     el `AccessError` del ticket; solo después aplicó la corrección. Revisé el diff y el traceback.
2. «Completa los tramos B y C del ejercicio 3.»
   - Encontró el segundo defecto (`self.env.user.commission_percent`) y que el fixture lo escondía. Propuso
     la contención por derecho de acceso manual, el script SQL de solo lectura y el plan de corrección.
3. Validar el script con datos: generar los datos del incidente con `t200_seed_incident.py` y comparar la
   salida con lo esperado, con una suma de control antes y después.

## Lo que la IA hizo mal
- **El script de datos falló dos veces.** La primera vez escribía las líneas con el entorno del vendedor
  (`AccessError`). La segunda generaba los pedidos sin seguimiento en el chatter y con el usuario equivocado
  en «confirmado por», porque hacía todo en una sola transacción. Lo detectamos al correr el script SQL: la
  columna salía vacía y luego con el vendedor en lugar del gerente. Se corrigió con un commit por acción,
  como pasa en producción.
- **Datos sin verificar en el primer borrador de INCIDENT.md:** decía que `./odoo` tenía un comando de
  respaldo (es `scripts/odoo_backup`) y daba mal el orden de los argumentos de `./odoo shell`. Se corrigió
  revisando el repositorio y `./odoo shell --help`.
- Para crear la base de pruebas a mano, primero corrió Odoo sin revisar los permisos del `filestore`, que
  habían quedado de `root` por `./odoo test`. La instalación falló con un error confuso en
  `res_lang_data.xml`. Se resolvió con `./odoo fix-files`.

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)
