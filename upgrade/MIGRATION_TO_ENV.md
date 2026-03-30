# Guía de Migración: Configuración por Variables de Entorno (.env)

Esta guía explica el proceso paso a paso para migrar nuestra infraestructura de `docker-odoo` hacia una arquitectura controlada enteramente por el archivo `.env`.

**Objetivo:** Permitir que los entornos de Desarrollo local y los Servidores de Producción gubernamentales/críticos compartan el mismo repositorio y archivo `docker-compose.app.yml` sin generar riesgos de seguridad ni conflictos en el código por personalizaciones fijas.

---

## PASO 1: Actualizar el `.env_example` (Y tu `.env` local)
**Prioridad: ALTA**

Para que el sistema sea dinámico, debemos registrar las variables base en el archivo `.env_example` para futuros proyectos, y en tu propio `.env` local para testear.

Agrega este bloque al final del archivo `.env_example`:

```bash
#####################################
# Configuraciones de Entorno Dinámico (Producción/Dev)
#####################################

# Modo de Arranque de Odoo (--dev=all para locales, dejar vacío en Producción)
ODOO_EXTRA_ARGS=--dev=all

# Exposición Segura de Puertos (0.0.0.0 para locales, 127.0.0.1 para Producción)
ODOO_PORT_BIND_IP=0.0.0.0

# Nginx: Nombre del servidor o IP pública (e.g. 190.202.28.109 o _ para locales)
NGINX_SERVER_NAME=_

# Nginx: Tamaños máximos y Timeouts para procesos largos (60s local, 7200s Producción)
NGINX_MAX_BODY_SIZE=200M
NGINX_PROXY_TIMEOUT=60s
```

## PASO 2: Convertir Nginx en un Sistema de Templates
**Prioridad: ALTA**

Nginx por defecto no lee variables del `.env` directamente en su código `.conf`. Para lograrlo debemos usar el sistema nativo de templates de la imagen oficial de Nginx.

1. Renombra tu archivo actual `.resources/nginx_configs/odoo.conf` a `odoo.conf.template` (la extensión `.template` es clave).
2. Modifica el archivo `.resources/nginx_configs/odoo.conf.template` cambiando los valores fijos por variables:

```nginx
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    client_max_body_size ${NGINX_MAX_BODY_SIZE};
    client_body_buffer_size ${NGINX_MAX_BODY_SIZE};

    # --- Timeouts globales pasados por entorno ---
    proxy_read_timeout ${NGINX_PROXY_TIMEOUT};
    proxy_send_timeout ${NGINX_PROXY_TIMEOUT};
    proxy_connect_timeout ${NGINX_PROXY_TIMEOUT};
    send_timeout ${NGINX_PROXY_TIMEOUT};

    location / {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $http_host;
        # ... resto de las cabeceras ...
        
        # Timeouts específicos para peticiones pesadas
        proxy_read_timeout ${NGINX_PROXY_TIMEOUT};
        proxy_send_timeout ${NGINX_PROXY_TIMEOUT};
    }

    location /websocket {
        proxy_pass http://odoo:8071;
        # ... resto de la configuración de websocket ...
        proxy_read_timeout ${NGINX_PROXY_TIMEOUT};
        proxy_send_timeout ${NGINX_PROXY_TIMEOUT};
    }
}
```

## PASO 3: Parametrizar el `docker-compose.app.yml`
**Prioridad: CRÍTICA**

Sustituiremos la configuración rígida actual por las variables preparadas en el paso 1, y además cambiaremos a dónde enrutamos los archivos de Nginx.

Abre el archivo `docker-compose.app.yml` y haz las siguientes modificaciones:

### Odoo Command y Ports
Remplaza la propiedad `command` y `ports` del servicio `odoo`:

```yaml
services:
  odoo:
    command: odoo -c /home/odoo/.config ${ODOO_EXTRA_ARGS:-}
    # ... otras configuraciones ...
    ports:
      # Si ODOO_PORT_BIND_IP no existe, asume 127.0.0.1 (cerrado al host) como medida de seguridad
      - "${ODOO_PORT_BIND_IP:-127.0.0.1}:8069:8069"
      - "${ODOO_PORT_BIND_IP:-127.0.0.1}:8071:8071"
```

### Nginx Templates
Inyecta las variables de entorno en el contenedor del proxy, y **(esto es vital)** cambia la ruta del `volumes` para que Nginx sepa que debe inyectar la data en tu template:

```yaml
  nginx:
    # ...
    environment:
      - NGINX_SERVER_NAME=${NGINX_SERVER_NAME:-_}
      - NGINX_MAX_BODY_SIZE=${NGINX_MAX_BODY_SIZE:-200M}
      - NGINX_PROXY_TIMEOUT=${NGINX_PROXY_TIMEOUT:-60s}
    volumes:
      # MUY IMPORTANTE: Se inyecta la carpeta entera a la ruta de templates de la imagen de Nginx
      - ./.resources/nginx_configs:/etc/nginx/templates
```

---

## PASO 4: Aplicar la Actualización en Producción (El Servidor del Cliente / Gobierno)
**Prioridad: CRÍTICA - MANUAL**

Una vez que todos tus cambios estén versionados en la rama principal de Git (`master`/`main`), debes ir al servidor de producción gubernamental y realizar el despliegue con extrema cautela para no afectar sus datos personalizados actuales.

1. **Respaldar el `.env` actual del cliente:**
   ```bash
   cp .env .env.backup
   ```
2. **Descargar tu nueva versión base:**
   Asegúrate de haber deshecho/limpiado cualquier cambio local manual que exista en el reporsitorio de su servidor para que al hacer `git pull` no hayan conflictos.
3. **Modificar SU archivo `.env`:**
   Abre el archivo `.env` local de su servidor con un editor (como Nano) y asigna los valores "quemados" que ellos requerían tener, inyectándolos a las nuevas variables de la modernización que realizaste:
   ```bash
   # En lugar de local usarán producción (vacío para desactivar Werkzeug y herramientas dev):
   ODOO_EXTRA_ARGS=
   
   # Para que Nginx los identifique en vez de "_"
   NGINX_SERVER_NAME=190.202.28.109
   
   # Odoo estará blindado a que el host no lo pueda leer desde afuera, Nginx es la única puerta:
   ODOO_PORT_BIND_IP=127.0.0.1

   # Sus configuraciones pesadas originales restauradas:
   NGINX_MAX_BODY_SIZE=10000M
   NGINX_PROXY_TIMEOUT=7200s
   ```
4. **Reiniciar la Infraestructura de los Contenedores:**
   Habiendo preparado el entorno local, se levanta con el *fuerza de recreación* ya que hay ajustes de templates:
   ```bash
   docker-compose -f docker-compose.app.yml down
   docker-compose -f docker-compose.app.yml up -d --build
   ```

Una vez finalizado esto, **ambos mundos conviven**: el código se vuelve limpio y reutilizable en tu repo, pero el cliente tiene su infraestructura pesada y personalizada totalmente aislada corriendo en producción.
