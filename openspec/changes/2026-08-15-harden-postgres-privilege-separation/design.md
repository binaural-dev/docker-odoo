# Decisiones técnicas

## Por qué no simplemente `ALTER ROLE odoo NOSUPERUSER`

Es la primera opción obvia y falla con:

```
ERROR:  permission denied to alter role
DETAIL:  The bootstrap user must have the SUPERUSER attribute.
```

Postgres protege específicamente al rol que ejecutó `initdb` (el "bootstrap
superuser", normalmente el rol con el oid más bajo asignable, oid=10 en la
práctica) — es una restricción del motor grabada a fuego, independiente del
nombre que se le haya dado al rol. Renombrarlo (como se hizo primero, de `odoo` a
`svc_pg16_a91c`/`svc_pg16o17_e47d`) no cambia su identidad interna ni esta
restricción.

## Por qué no `REASSIGN OWNED BY bootstrap TO app`

Mismo tipo de restricción, distinto mensaje:

```
ERROR:  cannot reassign ownership of objects owned by role svc_pg16_a91c
        because they are required by the database system
```

`ALTER DATABASE ... OWNER TO app` sí funciona (la propiedad a nivel de base de
datos no tiene esta restricción) y se aplicó en las 21+18 bases, pero eso no
alcanza: los objetos *dentro* de cada base (tablas, secuencias, schemas) siguen
siendo del bootstrap.

## Por qué `GRANT bootstrap TO app` sí funciona, y por qué es seguro

Dos mecanismos distintos de Postgres que conviene no confundir:

1. **Ownership-equivalent rights vía membresía**: el chequeo de permisos para
   operaciones que requieren ser dueño de un objeto (`ALTER TABLE`, `DROP TABLE`,
   etc.) usa `has_privs_of_role(rol_conectado, dueño_del_objeto)` — esta función
   SÍ sigue la cadena de membresías (`GRANT rolA TO rolB` con `INHERIT`, que es el
   default). Por eso `app`, siendo miembro de `bootstrap`, puede alterar tablas
   que son propiedad de `bootstrap` sin necesitar `SET ROLE`.
2. **`rolsuper` (superusuario)**: la función `superuser()` (y el chequeo de
   permisos internos que la usa, incluyendo el de `COPY ... FROM/TO PROGRAM`)
   mira el atributo `rolsuper` del rol de la sesión actual — **no** sigue cadenas
   de membresía. La única forma de "ser" superusuario en una sesión es tener
   `rolsuper=true` en el propio rol, o haber hecho `SET ROLE`/
   `SET SESSION AUTHORIZATION` explícito hacia un rol que sí lo tiene. Una
   conexión normal de Odoo jamás hace `SET ROLE`, así que `app` nunca actúa como
   superusuario aunque sea miembro de un rol que sí lo es.

Verificado empíricamente (no solo por lectura de documentación) en ambos
servicios antes de aplicar en las bases reales, usando un contenedor descartable
con volumen nuevo:

| Chequeo | Resultado |
|---|---|
| `SELECT current_setting('is_superuser')` conectado como `app` | `off` |
| `CREATE TABLE` / `ALTER TABLE ADD COLUMN` / `DROP TABLE` sobre una tabla del bootstrap, conectado como `app` | funciona |
| `COPY (SELECT 1) TO PROGRAM 'echo test'` conectado como `app` | `ERROR: permission denied to COPY to or from an external program` |
| `CREATE DATABASE` / `DROP DATABASE` conectado como `app` | funciona (tiene `CREATEDB`) |

## Por qué `NOLOGIN` en el bootstrap en vez de borrarlo

No se intentó `DROP ROLE` sobre el bootstrap — es razonable esperar que fallara
con el mismo tipo de restricción que `REASSIGN OWNED` (sigue siendo dueño de
objetos), pero no se comprobó. `NOLOGIN` logra el objetivo real (que nadie pueda
autenticarse como superusuario) sin arriesgar esa propiedad, que la membresía de
`app` sigue necesitando para funcionar. Es reversible con un solo
`ALTER ROLE ... LOGIN` si alguna vez hiciera falta una tarea puntual de
superusuario — usando el mecanismo de "break glass" descrito abajo.

## Cómo recuperar acceso de superusuario si alguna vez hace falta (break glass)

Con el bootstrap en `NOLOGIN`, no hay forma de autenticarse como superusuario por
red/SQL en ninguno de los dos servicios — a propósito. Si algún día hace falta
una operación genuinamente de superusuario (instalar una extensión no confiable,
`ALTER SYSTEM` sin haber delegado el parámetro puntual, etc.), el camino es:

1. `docker exec -it db-<servicio> bash`
2. Parar el proceso normal y arrancar Postgres en modo `--single` (bypasea toda
   la autenticación por rol, pensado para reparaciones de emergencia).
3. Hacer el cambio puntual (ej. `ALTER ROLE <bootstrap> LOGIN;`).
4. Volver a `NOLOGIN` y reiniciar en modo normal.

Esto requiere acceso real al servidor/Docker, no solo una credencial SQL filtrada
— que es exactamente el modelo de amenaza que se quiso cerrar.

## Alternativa descartada: delegar permisos puntuales sin crear un segundo rol

Postgres 15+ permite `GRANT SET ON PARAMETER <param> TO <rol>` y
`GRANT ALTER SYSTEM ON PARAMETER <param> TO <rol>` para delegar el manejo de
parámetros de configuración puntuales a un rol no-superusuario. Se evaluó como
posible camino para *tuning*/*logging* sin nunca haber necesitado superusuario,
pero no resuelve el problema de fondo (`COPY FROM PROGRAM`, que no es un
parámetro de configuración sino un privilegio de ejecución de programas del
servidor, gobernado por pertenencia al rol predefinido
`pg_execute_server_program` o por ser superusuario). Se documenta como opción
complementaria para delegar tuning puntual sin reabrir el rol bootstrap — ver el
cambio `2026-08-15-tooling-tuning-sighup-build-logs`.
