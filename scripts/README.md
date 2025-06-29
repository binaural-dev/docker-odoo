# Scripts disponibles

Esta carpeta agrupa utilidades para administrar y probar tu entorno de Odoo. La mayoría de los scripts hacen uso de las variables definidas en `.env`.

## migrate-module

```
./scripts/migrate-module -d <base_de_datos> -i <módulo> -c <contenedor>
```

Ejecuta la migración de un módulo dentro del contenedor indicado. Requiere el nombre de la base de datos, el módulo a migrar y el contenedor donde se ejecuta Odoo.

## odoo-backups.sh

Script para generar respaldos de bases de datos y filestore. Utiliza dos archivos de configuración (`config.json` y `servers.json`) para definir servidores y rutas de destino. Permite conectarse mediante SSH o de forma local.

## odoo-pw

```
./scripts/odoo-pw -d <base_de_datos> [-l <usuario>]
```

Restablece la contraseña de un usuario. Usa la variable `RESET_PASSWORD` del archivo `.env`. Por defecto actualiza al usuario `admin`.

## odoo-test

Ejecuta pruebas automatizadas sobre una base de datos llamada `testing`. Carga algunos módulos y etiquetas de prueba predefinidas.

## odoo-update

```
./scripts/odoo-update -d <base_de_datos> modulo1 modulo2 ...
```

Actualiza los módulos indicados en la base de datos especificada.

## restore_db.sh

```
./scripts/restore_db.sh -b <contenedor_db> -o <contenedor_odoo> -f <archivo.zip> -d <nombre_db>
```

Restaura un respaldo a partir de un archivo comprimido. Crea la base de datos, carga el volcado y copia el filestore si está presente.

