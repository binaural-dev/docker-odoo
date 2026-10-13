# odoo-cli-tooling

Capability que describe el comportamiento esperado del script de gestión
`/home/docker-odoo/odoo`.

## ADDED Requirements

### Requirement: Las operaciones sobre "todas las bases" deben respetar el alcance de la instancia

Cuando se listan o iteran bases de datos para una instancia específica, el CLI
DEBE limitarse a las bases que pertenecen a esa instancia (según su
`db_filter` efectivo), no a todas las bases del servicio de Postgres
compartido.

#### Scenario: `-d all` en una instancia con `db_filter` específico
- **GIVEN** una instancia cuyo `db_filter` efectivo matchea solo un subconjunto
  de las bases del servicio de Postgres que usa
- **WHEN** se listan sus bases de datos (ej. `./odoo update -d all -i
  <instancia>`)
- **THEN** solo deben incluirse las bases que matchean ese `db_filter`, no las
  de otras instancias que comparten el mismo servicio

#### Scenario: Instancia sin `db_filter` específico
- **GIVEN** una instancia cuyo `db_filter` es `"*"` o no está definido
- **WHEN** se listan sus bases de datos
- **THEN** se listan todas las bases del servicio (comportamiento previo,
  sin romper nada existente) pero se imprime una advertencia explícita

### Requirement: Actualizar "todos los módulos" no debe forzar una elección interactiva

Si no se especifica un módulo puntual, el CLI DEBE proceder a actualizar
todos los módulos sin desplegar una lista de selección.

#### Scenario: `./odoo update` sin `-m`
- **WHEN** se ejecuta `update` sin pasar `-m`
- **THEN** el CLI actualiza todos los módulos directamente, sin prompt
  interactivo de selección

### Requirement: Actualizar "todos los módulos" debe ser incremental por defecto

Actualizar todos los módulos DEBE, por defecto, tocar solo los módulos cuyo
contenido cambió desde la última actualización, no reprocesar literalmente
todos los módulos instalados.

#### Scenario: Actualización sin forzar
- **WHEN** se actualiza el destino "todos los módulos" sin el flag de forzado
- **THEN** el CLI usa una herramienta de actualización incremental (basada en
  hash de contenido) en vez de forzar el upgrade de cada módulo instalado

#### Scenario: Actualización forzada
- **GIVEN** se pasa el flag de forzado (`-f`/`--force`)
- **WHEN** se actualiza el destino "todos los módulos"
- **THEN** se fuerza un upgrade completo de todos los módulos instalados,
  sin importar si cambiaron

#### Scenario: Actualización de un módulo específico
- **GIVEN** se pasa un módulo puntual (`-m <modulo>`)
- **WHEN** se ejecuta `update`
- **THEN** se actualiza exactamente ese módulo, sin pasar por la lógica de
  actualización incremental ni por el flag de forzado

### Requirement: Medir cobertura de muchos módulos no debe reinstalar la base cada vez

Cuando se mide un módulo tras otro, el CLI DEBE poder partir de una plantilla de
base de datos ya poblada en vez de dejar que Odoo instale los módulos base desde
cero en cada corrida, y esa optimización NO DEBE alterar las cifras medidas.

#### Scenario: Correr con `--db-template`
- **GIVEN** una plantilla horneada con la misma versión de Odoo que el contenedor
- **WHEN** se corre `odoo-test <modulo> --db-template <plantilla>`
- **THEN** la base de test se clona de la plantilla, y el `pct`/`stmts`/`miss`
  del módulo es idéntico al que se obtiene sin plantilla

#### Scenario: La base clonada necesita su filestore
- **GIVEN** que clonar una base con `createdb -T` no clona su filestore
- **WHEN** se crea la base de test desde una plantilla
- **THEN** el filestore de la plantilla se copia junto con la base, y se borra
  con ella, para que ningún `ir_attachment.store_fname` apunte a un archivo
  ausente

### Requirement: Una suite trabada no debe colgar la corrida indefinidamente

El CLI DEBE poder cortar una corrida que exceda un tiempo dado, sin perder la
cobertura parcial ya recolectada y sin dejar recursos colgados.

#### Scenario: Corrida que excede el `--timeout`
- **WHEN** una corrida con `--timeout <s>` se pasa de ese tiempo
- **THEN** el proceso se corta DENTRO del contenedor (matar el cliente de
  `docker exec` no mataría el proceso de adentro), el reporte de cobertura
  parcial se genera igual, el resultado queda identificado con exit code 124 y
  `fail_reason: "timeout"`, y la base de datos y su filestore se borran

### Requirement: El resultado debe permitir distinguir "sin tests" de "no instala" en una sola pasada

El export de resultados DEBE incluir el estado real de instalación de cada
módulo leído de `ir_module_module`, no solo su forma derivada.

#### Scenario: Un módulo que reporta 0 % de cobertura
- **GIVEN** un módulo cuya corrida reporta 0 %
- **WHEN** se exporta el resultado con `--out-json`
- **THEN** el JSON incluye `module_states` con el `state` crudo de
  `ir_module_module`, de modo que un consumidor pueda saber si el 0 % es falta
  de pruebas o una instalación fallida **sin volver a instalar el módulo**

