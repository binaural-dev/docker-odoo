# Binaural Workspace

Binaural Workspace es un entorno de desarrollo diseñado para facilitar la ejecución y configuración de proyectos en Odoo. Con este repositorio, podrás levantar ambientes de desarrollo en Linux y macOS (AMD y ARM).

En cuanto a Windows, no se ha probado oficialmente, pero puede ser compatible utilizando WSL2 con Docker. Se recomienda verificar su funcionamiento en tu entorno antes de usarlo en producción.

## Instalación

Para comenzar a utilizar el espacio de trabajo, sigue los pasos a continuación.


### Clonar el repositorio:

```bash
git clone git@github.com:binaural-dev/docker-odoo.git
```

Accede al directorio:
```bash
cd docker-odoo
```

### Requerimientos

Instalar dotenv:

```bash
sudo apt-get install python3-dotenv
```

Esto es necesario para trabajar con el archivo de configuración .env, que almacenará todas las variables del entorno necesarias.

### Configurar el archivo .env

El archivo .env contiene las configuraciones para tu espacio de trabajo en Odoo. Deberás configurarlo antes de continuar. Puedes encontrar un archivo de ejemplo en el repositorio, el cual deberás modificar de acuerdo a tu entorno.

Para trabajar con la configuración por defecto, puedes ejecutar el siguiente comando para crear el .env

```bash
cp .env_example .env
```

> El .env_example está creado para levantar la versión 16.0 de Odoo. En caso de requerir una versión diferente, puedes cambiar el archivo .env actualizandos las referencias de 16.0 a 17.0.

### Clonar los Repositorios Necesarios (solo para miembros de Binaural)

Binaural trabaja con módulos alojados en distintos repositorios privados. En caso de que no formes parte de la organización, aún podrás levantar el ambiente sin problemas.

Clonar repositorios:
```bash
./odoo init
```

Los repo en cuestion son:
 - [Odoo Enterprise](https://github.com/odoo/enterprise) (necesitas ser partner odoo para tener acceso a este repositorio)
 - [Integra Addons](https://github.com/binaural-dev/integra-addons) (aplica solo para los devs de binaural)
 - [Third Party Addons](https://github.com/binaural-dev/third-party-addons) (aplica solo para los devs de binaural)

 Si no tienes acceso a estos repositorios comunicate con nuestro equipo de DevOps.

### Construcción del Dockerfile

El archivo de Dockerfile se construye a partir de las configuraciones de tu archivo .env (por ello es importante especificar la versión de Odoo a utilizar en dicho archivo).

 ```bash
./odoo build
```
### Estructura de la carpeta a utilizar

```bash
- src /
    custom/ (submodules de git)
        /repository-1 (repositorio/proyecto)
        /repository-2 (otro repositorio/proyecto)
        /repository-n (otro repositorio/proyecto más)
    integra-addons/
        /module-01
        /module-02
    enterprise/ (módulos enterprise de Odoo)
        /module-01
        /module-02
    third-party-addons/ (módulos de terceros)
        /module-01
        /module-02
```

En este entorno, los módulos de Odoo se organizan mediante submódulos de Git, lo que proporciona mayor flexibilidad y facilita la gestión del código.

La estructura ha sido diseñada para el flujo de trabajo de Binaural; sin embargo, el entorno funcionará sin problemas incluso si algunos módulos no están disponibles.

> Para más información sobre los módulos de binaural, puedes visitar [Odoo Venezuela](https://github.com/binaural-dev/odoo-venezuela)

> En caso de que no formes parte de la organización, no contarás con los repositorios de integra-addons, enterprise y third-party-addons. En ese caso, puedes desarrollar tus propios módulos en el directorio `custom`.

Si tienes deseas agregar o desarrollar algún módulo para tu ambiente, puedes hacerlo de dos formas:

- Agregar el módulo en third-party-addons
- Agregar un repositorio en custom

Para agregar un repositorio en custom, ubícate en docker-odoo/src/custom/ y ejecuta `git clone repositorio-que-contiene-tus-módulos.git`

### Inicio, Reinicio y Detención del Ambiente

Estos comandos son acortadores a los comandos naturales de `docker-compose`, tales como `up` y `down`.
```bash
./odoo run
./odoo restart
./odoo stop
```

### Acceso al Ambiente

El acceso a Odoo dependerá de la configuración establecida en el archivo .env.

- Opción 1: Acceso con Filtro de Base de Datos.

Si la variable DB_FILTER está activa en el .env, cada base de datos tendrá su propio subdominio (filtrado por el nombre de la base de datos). Esto permite acceder a distintas bases sin necesidad de seleccionarlas manualmente al ingresar al ambiente.

Ejemplo de acceso con DB_FILTER activo:
```bash
Base de datos "db"     →  db.odoo.localhost
Base de datos "prueba" →  prueba.odoo.localhost
Base de datos "17"     →  17.odoo.localhost
```

- Opción 2: Acceso General sin Filtro

Si no deseas utilizar el filtrado por dominio, simplemente comenta o elimina la variable DB_FILTER en el .env.

Ejemplo de acceso con DB_FILTER desactivado:
```bash
http://localhost:<PUERTO>
```

### Scripts útiles

En la carpeta [`scripts`](scripts/) encontrarás herramientas para realizar
distintas tareas de administración. Revisa la
[documentación de scripts](scripts/README.md) para conocer cada comando.

### FAQ

#### ¿Cómo configurar addons_path?

Cada vez que añades un nuevo repositorio a la carpeta custom, este será automáticamente detectado por el entorno.

#### ¿Qué es todo esto?
Para entender completamente el funcionamiento del entorno, te recomendamos familiarizarte con los comandos de la terminal de Linux, Docker, Traefik y, por supuesto, Odoo.

Si tienes alguna pregunta, no dudes en contactar con el equipo. Si no eres parte del equipo de desarrollo de Binaural, por favor utiliza los Issues en GitHub (siguiendo el código de conducta establecido).
