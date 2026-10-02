---
name: project-type-detect
description: Detecta si un proyecto cliente de Odoo es Homologado (tiene submodulo odoo-venezuela) u Operativo (solo integra-addons y third-party-addons), y deriva su version de Odoo. Usar cuando el usuario pregunte si un proyecto es homologado u operativo, o como paso previo antes de actualizar/tocar submodulos.
---

# project-type-detect

Determina, para un proyecto cliente — ya sea el directorio de trabajo actual (si es la raíz de un repo cliente) o `src/custom/<nombre>` (si se corre desde la raíz de docker-odoo) —, dos cosas de solo lectura:

1. **Tipo de proyecto**: Homologado u Operativo.
2. **Version de Odoo** (`MAYOR.MENOR`) y submodulos realmente presentes.

No escribe nada ni requiere confirmacion — es una consulta pura. Su logica se reutiliza (embebida, sin volver a preguntar nada) como primer paso de la skill `submodule-update`.

La distincion Homologado/Operativo es la version mecanica y local (por presencia de submodulo) de lo que las skills `odoo-repo-routing` y `odoo-localization-flow` (plugin `core`) explican a nivel conceptual: un proyecto Homologado es el que ya integra `odoo-venezuela` (localizacion) ademas de `integra-addons` (core reusable). Ver esas skills si hace falta el razonamiento de fondo, no solo la deteccion.

## Criterio de tipo de proyecto

- **Homologado**: el proyecto tiene el submodulo `odoo-venezuela` inicializado (existe la carpeta `odoo-venezuela/` con contenido, o al menos declarado en `.gitmodules`).
- **Operativo**: el proyecto solo tiene `integra-addons` y `third-party-addons` — no existe `odoo-venezuela`.

**Importante**: verificar por el `path` declarado en `.gitmodules`, no por el nombre de la seccion `[submodule "..."]`. Se confirmo en `src/custom/pcshop-core/.gitmodules` que la seccion se llama `homo-addons` pero el `path` real es `odoo-venezuela` (con un espacio final tras el nombre en ese archivo puntual — al comparar, hacer `trim` del valor leido):

```ini
[submodule "homo-addons"]
	path = odoo-venezuela
	url = git@github.com:binaural-dev/odoo-venezuela.git
```

## Flujo de trabajo

1. Resolver `PROJECT` (la raíz del repo cliente) sin asumir un unico punto de entrada:
   ```bash
   if [ -f ".gitmodules" ]; then
     PROJECT="."          # el cwd ya es la raiz del repo cliente
   elif [ -n "<nombre>" ] && [ -d "src/custom/<nombre>" ]; then
     PROJECT="src/custom/<nombre>"   # se esta corriendo desde la raiz de docker-odoo
   fi
   ```
   Si ninguna de las dos condiciones aplica (no hay `.gitmodules` en el cwd y no se dio un `<nombre>` valido bajo `src/custom/`), preguntar al usuario el proyecto objetivo — no asumir.

2. Leer `.gitmodules` del proyecto y extraer los `path` declarados:
   ```bash
   grep 'path = ' "$PROJECT/.gitmodules" | sed 's/.*path = //' | sed 's/[[:space:]]*$//'
   ```

3. Clasificar:
   - Si la lista incluye `odoo-venezuela` → **Homologado**.
   - Si no → **Operativo** (validar que al menos exista `integra-addons`; si ni siquiera eso existe, el proyecto no sigue la estructura esperada — avisar en vez de asumir).

4. Derivar `odoo_version` (mismo mecanismo que usa `docker-odoo-add-instance`):
   ```bash
   grep -h '"version"' "$PROJECT"/*/__manifest__.py 2>/dev/null
   ```
   Tomar el prefijo `MAYOR.MENOR` comun a los manifests del proyecto (ignorando los de los propios submodulos, que pueden ir un paso adelante/atras). Si no hay consenso claro, preguntar al usuario en vez de asumir.

5. Reportar en una linea o bloque corto: tipo de proyecto, `odoo_version`, y la lista de submodulos presentes (`integra-addons`, `odoo-venezuela` si aplica, `third-party-addons`).

## Salida esperada (ejemplo)

```
Proyecto: higea
Tipo: Homologado
Odoo version: 17.0
Submodulos presentes: integra-addons, odoo-venezuela, third-party-addons
```

```
Proyecto: lanprosystem
Tipo: Operativo
Odoo version: 17.0
Submodulos presentes: integra-addons, third-party-addons
```
