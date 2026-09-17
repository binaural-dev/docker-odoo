# Pendiente: Multi-ambiente en paralelo

## El problema

Con la estructura actual, **no se puede** levantar 2 copias de este repo
(clonadas en directorios distintos) en la misma máquina sin que se choquen.

## Recursos que chocan

Identificados en `.resources/generators/compose_generator.py`:

| Recurso | Valor actual | Línea | Choque |
|---------|--------------|-------|--------|
| `container_name` (DB) | `db-{db_name}` hardcodeado | 84, 97 | "name already in use" |
| `container_name` (Odoo) | `odoo-{inst_name}` hardcodeado | 124 | "name already in use" |
| Network | `NETWORK_NAME = "odoo-multi"` constante | 20 | la 2da instancia falla |
| Volúmenes con nombre | `v17-data`, `contiflex-data`, etc. | 110, 164, 167-169 | compartidos o falla |
| Port postgres | `5432` fijo en todas las DBs | (en `instances.json`) | bind error |
| Ports Odoo | `8070-8100` fijos en `instances.json` | (en `instances.json`) | bind error |
| Port nginx | fijo en config | (generador) | bind error |
| Port pgadmin | `5050` fijo | (en `instances.json`) | bind error |

## Opciones discutidas (no implementadas)

### Opción A — Mínimo viable (Recomendada por mí)
Quitar los `container_name:` hardcodeados. Docker compose prefixa
automáticamente con el project name (que viene del directorio o de
`-p`). Volúmenes: usar nombres anónimos. Network: usar el default de compose.

**Pro:** mínimo cambio de código, máximo resultado.
**Contra:** los ports siguen fijos; si dos copias del repo definen
`external_port: 8080` chocan. Solución: usar el port interno del contenedor
y mapear con `8080:8069` solo en una de las copias.

### Opción B — Configurable por proyecto
Agregar campo `project_prefix` (o `namespace`) en `instances.json`. Containers,
volúmenes, networks y ports se prefijan con ese valor.

**Pro:** control explícito, sin sorpresas.
**Contra:** requiere editar la config cada vez que clonás; más superficie
de error.

### Opción C — Solo documentar workaround
`COMPOSE_PROJECT_NAME=foo docker-compose up` en cada clon. Cero código.

**Pro:** nada que mantener.
**Contra:** requiere clonar el repo N veces (no se puede tener un solo clone
con múltiples "ambientes" lógicos); los ports siguen chocando.

## Lo mínimo a tocar (si se elige A)

1. `.resources/generators/compose_generator.py`:
   - Eliminar `container_name:` de los servicios de DB y Odoo
   - Eliminar el bloque `volumes:` con nombres explícitos al final
   - Reemplazar `NETWORK_NAME = "odoo-multi"` por `odoo-multi` solo como
     label, no como `name:` en la sección networks

2. Documentar el workflow multi-clone en `readme.md`:
   ```bash
   git clone <repo> work-foo
   cd work-foo
   ./odoo build
   COMPOSE_PROJECT_NAME=foo docker-compose up -d
   ```

## Estado

Conversación interrumpida antes de elegir opción. La pregunta quedó
cancelled por el usuario cuando pidió guardar el análisis acá.
