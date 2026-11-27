# Runbook ti-16739: quitar los volúmenes `py`/`py3` y activar la imagen nueva

## Problema

`docker-compose.app.yml` montaba dos volúmenes con nombre:

- `py3:/usr/local/lib/` (paquetes pip)
- `py:/usr/lib/` (Odoo instalado por el `.deb`, Python del sistema y librerías)

Se agregaron en f7a3e60 (2024-11-15, "[IMP] docker-compose: Volumen de
dependencias") para que lo que se instalaba con `pip` dentro del contenedor
sobreviviera a la recreación. El efecto secundario: Docker llena un volumen con
nombre desde la imagen **solo la primera vez**. Desde entonces cada `build`
nuevo queda tapado por el contenido viejo del volumen: el contenedor sigue
corriendo el Odoo y las librerías del día en que se creó el volumen.

En producción Bolipuertos (10.50.27.75) la imagen `local_odoo:18` del
2026-11-23 trae Odoo 18.0+e-20261124, pero el contenedor `proj` corre los
archivos de 2025-12-09 que están en `docker-odoo_py`/`docker-odoo_py3`
(creados el 2025-12-15). La actualización de seguridad no está activa.

En `master-multi` ya se corrigió en el generador (06ac5cc). Esta rama hace lo
mismo para `master` (compose único, el que usa el servidor).

## Cambios en la herramienta

- `docker-compose.app.yml`: sin montajes sobre `/usr/lib` ni
  `/usr/local/lib`, y sin declarar los volúmenes `py`/`py3`.
- `.resources/dockerfiles/18.0_Dockerfile`: instala en la imagen las dos
  dependencias que hasta ahora solo existían dentro de esos volúmenes:
  - `Authlib==1.6.12` (addon `mcp_server`, pide `>=1.6.12,<1.7.0`)
  - `httpagentparser==1.9.5` (addon `tk_security_master`)

  Van en una capa propia después de `requirements.txt`: un `build` con caché
  reutiliza la capa del `.deb` de Odoo y no baja una nightly distinta.

Si a futuro un addon necesita otra librería, se agrega en el Dockerfile y se
reconstruye la imagen. No se instala a mano dentro del contenedor: sin los
volúmenes eso se pierde al recrearlo.

## Ojo con el servidor de producción

- `~/docker-odoo` está en `master` en d9125b6 (18 commits detrás de
  `origin/master`) y tiene cambios locales sin commitear (y parte en el
  índice) en `docker-compose.app.yml`, `odoo`, `scripts/odoo_backup`,
  `.resources/nginx_configs/odoo.conf` y `scripts/odoo_restore` borrado.
  **No hacer `git pull` ni `git checkout`**: se pisan esos cambios. Los dos
  cambios de esta rama se aplican a mano (pasos 3 y 4).
- `docker-compose.app.yml` no lo genera la herramienta en `master`: es un
  archivo versionado y en el servidor está editado a mano (DNS internos,
  puertos 8069/8071, `image: local_odoo:${ODOO_MINOR}`, red `odoo-18.0`).
- `.resources/Dockerfile` sí es generado: `./odoo build` concatena
  `.resources/dockerfiles/${ODOO_VERSION}_Dockerfile` +
  `.resources/Dockerfile.template` y corre `docker compose build`.
- Contenedor: `proj`; proyecto compose: `docker-odoo`; volúmenes a retirar:
  `docker-odoo_py` y `docker-odoo_py3`.

## Pasos (ventana de mantenimiento)

Todo desde `~/docker-odoo` como `binaural`. Hay corte de servicio entre el
paso 6 y el 7 (segundos a pocos minutos).

1. **Respaldo** de la base y el filestore con el script habitual
   (`scripts/odoo_backup`) y confirmar que el zip quedó completo. Guardar
   copia de los archivos que se van a tocar:

   ```bash
   cp docker-compose.app.yml docker-compose.app.yml.bak-ti16739
   cp .resources/dockerfiles/18.0_Dockerfile .resources/dockerfiles/18.0_Dockerfile.bak-ti16739
   ```

2. **Etiquetar la imagen actual** para poder volver:

   ```bash
   docker tag local_odoo:18 local_odoo:18-pre-ti16739
   docker inspect proj --format '{{.Image}}'   # anotar el sha
   ```

3. **Dockerfile**: agregar al final de
   `.resources/dockerfiles/18.0_Dockerfile` el bloque de esta rama:

   ```dockerfile
   RUN python3 -m pip install --no-cache-dir \
       Authlib==1.6.12 \
       httpagentparser==1.9.5
   ```

4. **Compose**: en `docker-compose.app.yml` borrar las líneas
   `- py3:/usr/local/lib/` y `- py:/usr/lib/` del servicio `odoo`, y `py3:` y
   `py:` de la sección `volumes:` del final. No tocar nada más. Validar:

   ```bash
   docker compose -f docker-compose.app.yml config -q && echo OK
   docker compose -f docker-compose.app.yml config | grep -n '/usr/' || echo "sin montajes en /usr"
   ```

5. **Construir con caché** (sin `--no-cache`, para no cambiar de nightly):

   ```bash
   ./odoo build
   ```

   Verificar la imagen **antes** de tocar el contenedor:

   ```bash
   docker run --rm --entrypoint python3 local_odoo:18 -c \
     "import odoo.release as r, authlib, httpagentparser; print(r.version, authlib.__version__)"
   ```

   Debe imprimir `18.0+e-20261124` (o la fecha de la imagen que se
   construyó) y `1.6.12`. Si la caché no estaba y bajó otra nightly, la fecha
   será posterior: frenar y decidir si se sigue (habría que probarla en QA).

6. **Recrear el contenedor** (el `restart` no basta: hay que recrearlo para
   que deje de montar los volúmenes):

   ```bash
   docker compose -f docker-compose.app.yml up -d --force-recreate odoo
   ```

   No usar `down -v`: borraría también `odoo-web` y `odoo_data` (filestore).

7. **Verificar**:

   ```bash
   docker inspect proj --format '{{range .Mounts}}{{.Destination}} {{end}}'
   # no debe aparecer /usr/lib ni /usr/local/lib
   docker exec proj python3 -c "import odoo.release as r; print(r.version, r.version_info)"
   # esperado: la versión de la nightly 20261124
   docker exec proj sh -c "dpkg-query -W -f='\${Version}\n' odoo; stat -c %y /usr/lib/python3/dist-packages/odoo/release.py"
   # dpkg vive en /var/lib y siempre mostró la versión nueva; la fecha de
   # release.py (en /usr/lib) es la que delata si sigue el código viejo
   docker exec proj python3 -c "import authlib, httpagentparser; print(authlib.__version__)"
   curl -s -X POST -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","method":"call","params":{}}' \
     http://localhost:8069/web/webclient/version_info
   # server_version_info con la fecha 20261124
   docker logs --tail=200 proj 2>&1 | grep -iE 'error|pip|requirement'
   ```

   El entrypoint `400-auto-detect-addons` corre `pip install -r` del
   `requirements.txt` de cada carpeta de `src/custom` en cada arranque
   (`bolipuertos-v18` pide, entre otros, `openpyxl>=3.1.0`). Sin el volumen,
   lo que no esté en la imagen lo instala pip en `~/.local` del usuario
   `odoo`, dentro del contenedor: necesita salida a PyPI/GitHub y se repite
   cada vez que se recrea. Revisar en el log que ese paso terminó bien; si
   instala algo, agregarlo al Dockerfile en un cambio aparte.

   Prueba funcional: login, abrir un módulo de `mcp_server` y el registro de
   accesos de `tk_security_master`, imprimir un reporte PDF.

8. **Solo si todo lo anterior está bien** (dejar pasar al menos un día de
   operación), borrar los volúmenes viejos:

   ```bash
   docker ps -a --filter volume=docker-odoo_py --filter volume=docker-odoo_py3   # debe salir vacío
   docker volume rm docker-odoo_py docker-odoo_py3
   ```

   En el servidor también quedan `swar_py`, `swar_py3`, `swarm_odoo_py` y
   `swarm_odoo_py3` de despliegues anteriores. No son de este proyecto:
   revisar con `docker ps -a --filter volume=<nombre>` antes de decidir.

## Rollback

Mientras no se hayan borrado los volúmenes (paso 8), volver es inmediato:

```bash
cp docker-compose.app.yml.bak-ti16739 docker-compose.app.yml
cp .resources/dockerfiles/18.0_Dockerfile.bak-ti16739 .resources/dockerfiles/18.0_Dockerfile
docker tag local_odoo:18-pre-ti16739 local_odoo:18
docker compose -f docker-compose.app.yml up -d --force-recreate odoo
```

Eso deja el servicio exactamente como estaba (incluido el Odoo de 2025-12-09
del volumen, es decir **sin** la actualización de seguridad). Si el problema
es de datos y no de código, restaurar el respaldo del paso 1.

## QA / staging (10.50.27.76)

Antes de producción, revisar lo mismo en QA:

```bash
docker inspect <contenedor> --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{println}}{{end}}'
docker exec <contenedor> python3 -c "import odoo.release as r; print(r.version)"
```

Si monta `/usr/lib` o `/usr/local/lib`, tiene el mismo problema y conviene
ensayar este runbook ahí primero.
