# odoo-container-startup

Capability que describe cómo debe comportarse el arranque de un contenedor
`odoo-*` cuando su servicio de Postgres no está disponible.

## ADDED Requirements

### Requirement: La espera por Postgres debe estar acotada en el tiempo

El script de espera (`entrypoint.d/600-wait-postgress`) DEBE dejar de
reintentar después de `WAIT_PG_TIMEOUT` segundos (default 300) y terminar con
código de salida distinto de cero, en vez de reintentar indefinidamente.

#### Scenario: Postgres nunca responde
- **GIVEN** un contenedor `odoo-*` arrancando con `WAIT_PG=true` y Postgres
  inalcanzable
- **WHEN** pasan `WAIT_PG_TIMEOUT` segundos sin que Postgres responda
- **THEN** el script debe terminar con `exit 1` y un mensaje de error, dejando
  que la política de reinicio del contenedor (`restart: always`) tome el
  control

### Requirement: Los reintentos no deben acumular procesos

Cada intento fallido de conexión DEBE resolverse dentro de la misma
iteración de un loop, sin dejar procesos o subshells previos colgados
esperando.

#### Scenario: Varios reintentos seguidos
- **GIVEN** Postgres tarda varios segundos en responder
- **WHEN** el script reintenta cada segundo mientras espera
- **THEN** en cualquier momento debe existir como máximo un proceso de esta
  espera vivo por contenedor (no uno acumulado por cada intento fallido)
