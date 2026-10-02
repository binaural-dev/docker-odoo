# upgrade/

Checklists de compatibilidad estructural para saltos de version de Odoo (16→17, 17→18, 18→19, ...), usados por la skill `mig-version-upgrade` (`docker-odoo/.claude/agents/mig-version-upgrade/SKILL.md`).

## Que es un checklist aqui

Un archivo `checklists/<origen>-<destino>.md` (ej. `checklists/16.0-17.0.md`) con reglas conocidas de cambios estructurales entre esas dos versiones de Odoo: assets renombrados, vistas que cambian de motor, decoradores/API removidos, patrones de reescritura de frontend, etc. Cada regla indica severidad (Bloqueante / Recomendado / Informativo) y, cuando se conoce, un ejemplo antes/despues.

## Como se alimenta

`mig-version-upgrade` lee el checklist del salto correspondiente **antes** de evaluar un proyecto (mismo principio que el estandar OpenSpec+Tests: se lee antes de generar). Cuando encuentra en una corrida real un cambio no catalogado — confirmado contra el diff real del nucleo (`src/enterprise-<origen>` vs `src/enterprise-<destino>`, o `src/odoo`), no solo por sospecha — lo propone como nueva entrada. **Nunca se guarda una entrada nueva sin que el usuario la confirme explicitamente** (afecta a todos los proyectos que usen ese checklist despues).

Si el checklist para un salto especifico no existe todavia, `mig-version-upgrade` lo crea desde cero con lo que encuentre en esa primera corrida.

## Convencion de nombres

`checklists/<version_origen>-<version_destino>.md`, usando el mismo formato `MAYOR.MENOR` que `project-type-detect` deriva de los manifests (ej. `16.0-17.0.md`, no `16-17.md`).
