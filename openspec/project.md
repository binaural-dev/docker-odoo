# docker-odoo — contexto del proyecto

## Qué es

Infraestructura multi-instancia de Odoo sobre Docker Compose. `instances.json` es la
única fuente de verdad: define bases de datos gestionadas (`databases`), instancias
de Odoo (`instances`), configuración por defecto (`odoo_configs`) y, opcionalmente,
pgAdmin. El script `/home/docker-odoo/odoo` (CLI) y los generadores en
`.resources/generators/` (`compose_generator.py`, `dockerfile_generator.py`,
`nginx_generator.py`, `config_loader.py`) leen ese archivo y producen
`docker-compose.generated.yml`, Dockerfiles por versión de Odoo y la config de nginx.

`instances.json` y `docker-compose.generated.yml` están en `.gitignore` — nunca se
commitean (contienen contraseñas reales).

## Arquitectura relevante

- Cada base de datos gestionada (`pg16`, `pg16_odoo_17`, ...) corre en su propio
  contenedor Postgres (`db-<nombre>`), con su propio clúster/volumen.
- Cada base tiene dos identidades de Postgres desde el hardening de 2026-08-15:
  - **bootstrap**: el rol que Postgres crea al inicializar el clúster (`initdb`).
    Siempre superusuario — Postgres no permite quitarle ese atributo ni
    reasignarle la propiedad de sus objetos ("required by the database system").
    Se deja en `NOLOGIN`: existe, es dueño de los objetos originales, pero nadie
    puede autenticarse con él.
  - **app**: rol no-superusuario (`LOGIN CREATEDB`) que hereda los privilegios de
    owner del bootstrap vía `GRANT bootstrap TO app` (para que los `ALTER TABLE` de
    updates de módulos sigan funcionando), pero sin heredar nunca el bit de
    superusuario (eso en Postgres solo se obtiene por atributo propio o `SET ROLE`
    explícito). Es el que usa Odoo para todo.
- Publicar puertos de Postgres al host es opt-in (`expose_host_port` en la config
  de cada base, default `false`) — por defecto solo son alcanzables entre
  contenedores hermanos vía la red interna `odoo-multi`.
- nginx es el único punto de entrada público (puerto 80, y los `external_port` de
  cada instancia para acceso directo).

## Convenciones de commits

Mensajes en español, prefijo `[FIX]`/`[FEAT]` + área afectada, resumen corto en el
subject, y cuerpo explicando el *por qué* (motivación/incidente/analogía), no solo
el qué — el código ya dice el qué.
