# Binaural Workspace

## Instalación

Para Empezar a utilizar el espacio de Trabajo, debes realizar diversos comandos, los cuales te ire exiplcando cuando usar cada uno (Porque lo puedes seguir usando fuera de la instalacion)

### Requerimientos

Instalar dotenv

```bash
sudo apt-get install python3-dotenv 
```

### Configurar el archivo .env

En este archivo se encuentra lo necesario para configurar tu entorno de Trabajo con Odoo. 

### Clonar los Repositorios Necesarios

Ya cuando hayas configurado la version dentro del archivo .env, puedes proceder a este comando, nos permitira clonar los repositorios necesarios para el desarrollo.

```bash
./odoo init
```
    
Como lo son:
 - [Odoo Enterprise](https://github.com/odoo/enterprise)
 - [Integra Addons](https://github.com/binaural-dev/integra-addons)
 - [Third Party Addons](https://github.com/binaural-dev/third-party-addons)

 Si no tienes acceso a estos repositorios comunicate con el equipo.

 ### Buildear el Dockerfile

 Inicialmente no existe el Dockerflie, ya que se require que se llene Informacion dentro del .env asi como la version, este comando nos generara el Dockerfile ideal para utilizarlo en nuestro entorno de trabajo.

 ```bash
./odoo build
```
### Estructura de la carpeta a utilizar

```bash
- src /
    custom/
        /repository-1
        /repository-2
        /repository-n
    integra-addons/
    enterprise/
    third-party-addons/
```

### Inicio, Reinicio y Stop del Ambiente

Estos comandos son acortadores a los comandos naturales de docker compose. como up y down.
```bash
./odoo run
./odoo restart
./odoo stop
```

### Acceso al Ambiente

El ambiente se posiciona en  
```bash
url odoo.localhost
```
porque esta contiene la opcion de dbfilter,
lo que nos permite filtrar las bases de datos por su dominio, es decir:
En caso de no querer filtrarlo, comentar en el .env "DB_FILTER"

```bash
Base de datos "db": db.odoo.localhost
Base de datos "prueba": prueba.odoo.localhost
Base de datos "17": 17.odoo.localhost
```

### FAQ

#### Donde configuro el addons_path?

Al incluir un repositorio nuevo a la carpeta custom, este lo detectara automaticamente.

