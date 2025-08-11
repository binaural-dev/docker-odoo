# Scripts disponibles

Esta carpeta agrupa utilidades para administrar y probar tu entorno de Odoo. La mayoría de los scripts hacen uso de las variables definidas en `.env`.




## Ejemplos de uso de scripts

### migrate-module

```sh
./scripts/migrate-module -d <base_de_datos> -i <modulo> -c <contenedor_odoo>
```
Migra el módulo `<modulo>` en la base de datos `<base_de_datos>` dentro del contenedor `<contenedor_odoo>`.

### odoo-backups.sh

```sh
./scripts/odoo-backups.sh -c <config.json> -s <servers.json> -d <base_de_datos>
```
Genera un respaldo de la base de datos `<base_de_datos>` y su filestore, utilizando los archivos de configuración y servidores indicados.

### odoo-pw

```sh
./scripts/odoo-pw -d <base_de_datos> -l <usuario>
```
Restablece la contraseña del usuario `<usuario>` en la base de datos `<base_de_datos>`, usando el valor de `RESET_PASSWORD` definido en el archivo `.env`. Si no se indica usuario, se restablece la contraseña de `admin`.

### odoo-test

```sh
./scripts/odoo-test
```
Ejecuta pruebas automatizadas sobre la base de datos `testing`.

### odoo-update

```sh
./scripts/odoo-update -d <base_de_datos> <modulo1> <modulo2> ...
```
Actualiza los módulos indicados (`<modulo1>`, `<modulo2>`, etc.) en la base de datos `<base_de_datos>`.

### restore_db.sh

```sh
./scripts/restore_db.sh -b <contenedor_db> -o <contenedor_odoo> -f <archivo_backup> -d <base_de_datos>
```
Restaura el backup `<archivo_backup>` en la base de datos `<base_de_datos>`, utilizando los contenedores `<contenedor_db>` (PostgreSQL) y `<contenedor_odoo>` (Odoo).


### Notas y solución de problemas para restore_db.sh

- El script detecta automáticamente si el archivo es `.dump` (usa `pg_restore`) o `.sql` (usa `psql`).
- Si ves el error `pg_restore: error: unsupported version (1.16) in file header`, significa que tu contenedor de PostgreSQL es más antiguo que la versión usada para generar el dump.  
  **Solución:** actualiza la variable `POSTGRES_IMG_VERSION` en tu `.env` y recrea el contenedor.
- Si después de restaurar y actualizar todos los módulos aparecen errores como `KeyError: 'ir.http'` en Odoo, puede deberse a:
  - Un dump incompleto o corrupto.
  - Falta de módulos en el path de addons.
  - Incompatibilidad entre la versión de Odoo y la base restaurada.
- Para máxima compatibilidad, solicita siempre el dump en formato SQL plano (`.sql`).
- Si tienes problemas, revisa los logs de restauración y asegúrate de que todos los módulos requeridos estén presentes en el entorno.

