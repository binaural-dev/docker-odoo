# Arreglar fuga de procesos en 600-wait-postgress cuando Postgres no responde

**Estado: implementado y verificado (2026-08-15).**

## Por qué

El usuario reportó un incidente reciente en otro servidor que administra: al
caerse el servicio de Postgres, los contenedores de Odoo quedaron acumulando
procesos sin límite (640+ simultáneos), consumiendo toda la RAM del servidor.

Causa raíz encontrada en `.resources/entrypoint.d/600-wait-postgress` (parte de
la cadena de arranque de cualquier contenedor `odoo-*`, corre antes de que
Odoo mismo levante):

```bash
function db_is_listening() {
    psql --list > /dev/null 2>&1 || (sleep 1 && db_is_listening)
}
function pg_user_exist() {
    psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PGUSER'" > /dev/null 2>&1 || (sleep 1 && pg_user_exist)
}
```

Esto **no es un loop** — es recursión de bash dentro de subshells
(`|| (sleep 1 && funcion)`). Cada intento fallido no reintenta *en el mismo
proceso*: crea un subshell nuevo que vuelve a llamar a la función, la cual
queda esperando a que ese subshell hijo termine. Como no hay `exec` (que
reemplazaría el proceso actual), cada fallo apila un nivel más de
subshell+psql **sin liberar el anterior** — el proceso original sigue vivo,
bloqueado, esperando a su hijo. Sin límite de tiempo ni de intentos: si
Postgres tarda en volver (o nunca vuelve), cada contenedor `odoo-*` que esté
en esta espera acumula aproximadamente un proceso nuevo por segundo,
indefinidamente. Con varios contenedores golpeados por la misma caída de
Postgres a la vez, la cantidad de procesos acumulados se multiplica — que es
exactamente el patrón de "640+ procesos" reportado.

## Qué cambia

`.resources/entrypoint.d/600-wait-postgress` reescrito para usar loops reales
(`until ... do ... done`) en vez de recursión por subshells, con un límite de
tiempo configurable (`WAIT_PG_TIMEOUT`, default 300s = 5 minutos). Si Postgres
no responde dentro de ese tiempo, el script termina con `exit 1` y un mensaje
de error claro, en vez de seguir esperando para siempre. Combinado con
`restart: always` en el servicio de Odoo (ya presente en
`docker-compose.generated.yml`), esto deja que Docker reinicie el contenedor
con un proceso limpio en vez de que el propio script acumule cadenas de
procesos internamente.

## Impacto

- Sin este límite, un Postgres caído por tiempo prolongado podía, en el peor
  caso, dejar cientos de procesos colgados por contenedor — con varios
  contenedores afectados a la vez, suficiente para agotar la RAM del host (tal
  como ya sucedió en otro servidor).
- Con el fix: como máximo `WAIT_PG_TIMEOUT` segundos de espera con un solo
  proceso vivo per intento (sin acumulación), y después el contenedor falla
  limpio y se reinicia solo.
- Validado en un test aislado (binario `psql` simulado que siempre falla):
  con `WAIT_PG_TIMEOUT=3`, el script corta a los 3 segundos con
  `exit code 1` y el mensaje de error esperado, sin procesos huérfanos.
- No se tocó `.resources/wait-for-psql.py` (otro script de espera, usado en
  otro punto del arranque) — ya usaba un loop acotado con timeout desde el
  principio, no tenía este problema.
