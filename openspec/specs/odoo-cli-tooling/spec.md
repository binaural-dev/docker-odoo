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
