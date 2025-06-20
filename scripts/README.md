# Scripts auxiliares

Esta carpeta contiene utilidades para facilitar tareas comunes al trabajar con Odoo.

## migrate-module
Ejecuta la migración de un módulo dentro de una base de datos específica.

```
./migrate-module -d <basedatos> -i <modulo> -c <contenedor>
```

Ejemplo:

```
./migrate-module -d prueba -i my_module -c odoo
```

## odoo-backups.sh
Genera respaldos de bases de datos y filestore de distintos servidores. Requiere los archivos `servers.json` y `config.json` con la configuración de cada servidor.

```
./odoo-backups.sh
```

## odoo-pw
Permite restablecer la contraseña de un usuario en una base de datos.

```
./odoo-pw -d <basedatos> [-l <login>]
```

Ejemplo:

```
./odoo-pw -d prueba -l admin
```

## odoo-test
Ejecuta pruebas automáticas dentro del contenedor de Odoo.

```
./odoo-test
```

El script define la base de datos y etiquetas de prueba que necesita.

## odoo-update
Actualiza uno o más módulos dentro de una base de datos.

```
./odoo-update -d <basedatos> <modulo1 modulo2 ...>
```

Ejemplo:

```
./odoo-update -d prueba modulo_a modulo_b
```

## restore_db.sh
Restaura una base de datos y su filestore a partir de un archivo comprimido.

```
./restore_db.sh -b <contenedor_db> -o <contenedor_odoo> -f <backup.zip> -d <basedatos>
```

Ejemplo:

```
./restore_db.sh -b db_container -o odoo_container -f backup.zip -d prueba
```

