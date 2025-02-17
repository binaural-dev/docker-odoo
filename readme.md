# Binaural Workspace

Este repo te permitira ejecutar en ambientes de desarrollo todos los proyectos que necesites echar a andar en Odoo. Aca podrás levantar ambientes de prueba con linux y mac (no estoy claro si se ha probado en Wintendo,
quiza funcione)

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

Cuando hayas configurado la version dentro del archivo .env, puedes ejecutar el siguiente comando, el cual permitira clonar los repositorios necesarios para el desarrollo.

```bash
./odoo init
```
    
Los repo en cuestion son:
 - [Odoo Enterprise](https://github.com/odoo/enterprise) (necesitas ser partner odoo para tener acceso a este repo)
 - [Integra Addons](https://github.com/binaural-dev/integra-addons) (aplica solo para los devs de binaural)
 - [Third Party Addons](https://github.com/binaural-dev/third-party-addons) (aplica solo para los devs de binaural)

 Si no tienes acceso a estos repositorios comunicate con nuestro devops.

 ### Buildear el Dockerfile

 Inicialmente no existe el archivo Dockerflie, ya que se require que se llene Informacion dentro del .env asi como la version, este comando generará el Dockerfile ideal para utilizarlo en nuestro entorno de trabajo.

 ```bash
./odoo build
```
### Estructura de la carpeta a utilizar

```bash
- src /
    custom/
        /repository-1 (un proyecto)
        /repository-2 (otro proyecto)
        /repository-n (otro proyecto mas)
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

#### Que es todo esto que hablan aca?

Para poder entender el funcionamiento te recomendamos que te des una pasada por shell de linux, docker, traefik y obviamente odoo.

Cualquier duda puedes preguntar al equipo, en caso que no seas del equipo de devs de binaural puedes usar los issues (cumpliendo con el codigo de conducta establecido)

