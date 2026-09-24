# odoo-version-support

Capability que describe cómo este repo agrega soporte para una versión de
Odoo nueva (Dockerfile por versión, sin lógica hardcodeada por versión en
los generadores).

## ADDED Requirements

### Requirement: Agregar una versión de Odoo solo requiere su Dockerfile fuente

Ninguno de los generadores (`config_loader.py`, `dockerfile_generator.py`,
`compose_generator.py`) DEBE tener una lista de versiones de Odoo
soportadas hardcodeada. Agregar soporte para una versión nueva DEBE
alcanzar con crear `.resources/dockerfiles/<version>_Dockerfile` — el
resto de la generación (Dockerfile final, servicio en
`docker-compose.generated.yml`) funciona para cualquier `odoo_version`
usada en `instances.json` sin tocar código de los generadores.

#### Scenario: instancia con una versión de Odoo nueva
- **GIVEN** `instances.json` tiene una instancia con `odoo_version`
  distinta a las ya usadas, y existe
  `.resources/dockerfiles/<version>_Dockerfile`
- **WHEN** se generan los Dockerfiles y el compose (`./odoo build`, o
  `generate_dockerfiles()`/`generate_compose()` directamente)
- **THEN** se genera `.resources/Dockerfile.<version>` (concatenación de
  `dockerfiles/<version>_Dockerfile` + `Dockerfile.template`) y el
  servicio `odoo-<instancia>` en el compose generado apunta a ese
  Dockerfile, sin errores

#### Scenario: falta el Dockerfile fuente de la versión
- **GIVEN** `instances.json` tiene una instancia con un `odoo_version`
  para el que NO existe `.resources/dockerfiles/<version>_Dockerfile`
- **WHEN** se corre la generación de Dockerfiles
- **THEN** el CLI aborta con un error explícito nombrando la versión y la
  ruta esperada, antes de tocar Docker

### Requirement: Odoo 20.0 es una versión soportada

`.resources/dockerfiles/20.0_Dockerfile` DEBE existir, resolviendo en
build-time (no hardcodeado) los paquetes apt (`debian/control`) y pip
(`requirements.txt`) de la rama `20.0` real de `odoo/odoo`, sobre la misma
imagen base (`ubuntu:noble`) que ya usan 17.0/19.0.

#### Scenario: instancia Odoo 20.0
- **WHEN** una instancia de `instances.json` declara `"odoo_version":
  "20.0"`
- **THEN** el CLI la trata igual que cualquier otra versión soportada:
  genera su Dockerfile y su servicio de compose sin necesitar ningún
  cambio de código adicional
