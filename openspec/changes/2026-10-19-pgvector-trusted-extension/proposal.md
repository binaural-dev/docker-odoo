# pgvector como extensión confiable (`trusted`) para instalar `ai` en Odoo 20

**Estado: implementado (2026-10-19).**

## Por qué

El módulo `ai` de Odoo 20 (enterprise) ejecuta en su `pre_init_hook`
`CREATE EXTENSION IF NOT EXISTS vector` sobre la base donde se instala. Desde
la separación de privilegios (`2026-08-15-harden-postgres-privilege-separation`)
Odoo se conecta con un rol que nunca es superusuario, y `pgvector` no viene
marcado como `trusted`, así que la instalación fallaba con:

```
psycopg2.errors.InsufficientPrivilege: permission denied to create extension "vector"
HINT:  Must be superuser to create this extension.
```

El paquete `postgresql-<v>-pgvector` ya estaba instalado en la imagen; lo
que faltaba era permiso para crear la extensión. La única salida era el
break-glass del rol bootstrap a mano, por cada base.

## Qué cambia

- **`.resources/db.Dockerfile`**: después de instalar `pgvector`, agrega
  `trusted = true` a `vector.control`. Con eso, cualquier rol con privilegio
  `CREATE` sobre la base (el dueño, o sea el rol de la instancia) puede
  crear la extensión. Postgres la instala internamente como el superusuario
  de arranque, sin que el rol de la instancia gane privilegios extra.
- **`.resources/db_install_extensions.sh`**: el chequeo de arranque ahora
  verifica que `vector` esté disponible **y** marcado como `trusted`.

Como el `.control` vive en la imagen y no en `PGDATA`, el cambio aplica
también a volúmenes de datos existentes: basta con reconstruir la imagen
del servicio de Postgres y recrear su contenedor (`./odoo build` /
`docker compose build db-<v> && docker compose up -d db-<v>`).

## Por qué `trusted` y no otra alternativa

- **Extensión en `template1`**: no cubre bases ya existentes, y Odoo crea
  bases desde `template0` por defecto (`db_template`).
- **`SUPERUSER` temporal / break-glass al instalar**: el break-glass
  reinicia todo el servicio de Postgres y requiere intervención; no encaja
  en un "Instalar" desde la UI de Odoo.
- `pgvector` solo define un tipo de dato, operadores y métodos de acceso de
  índice; no expone funciones que permitan escalar privilegios (archivos,
  red, ejecución de programas). Marcarlo `trusted` no rompe el requisito
  de `postgres-security` de que el rol de Odoo nunca sea superusuario.

## Fuera de alcance

- `scripts/odoo_restore` sigue otorgando `SUPERUSER` temporal cuando el dump
  trae `CREATE EXTENSION IF NOT EXISTS` (cubre otras extensiones no
  confiables). Para dumps que solo traen `vector` ya no haría falta, pero no
  se cambia ese comportamiento acá.

## Verificado

- `docker compose build db-v20` + `up -d db-v20` sobre un volumen existente:
  `pg_available_extension_versions` reporta `vector 0.8.7 | trusted = t`.
- Como rol `odoo` (no superusuario): `createdb pgv_trust_test`,
  `CREATE EXTENSION IF NOT EXISTS vector` y una consulta
  `'[1,2]'::vector <-> '[1,3]'::vector` funcionan sin error; base borrada
  después.
