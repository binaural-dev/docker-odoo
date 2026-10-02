---
name: verificar-referencia-modulo
description: Verifica si una referencia (modulo + external ID) sigue siendo funcional en una ubicacion destino determinada -- otro submodulo en el mismo checkout, u otra rama de version del mismo submodulo, sin necesidad de hacer checkout -- y devuelve un veredicto estandar (FUNCIONAL / RENOMBRADO / HUERFANO / CODIGO_MUERTO). No se usa sola: es un sub-paso que otras skills de migracion aplican embebido, con su propio criterio de que hacer con cada veredicto. Usar dentro de mig-customs-to-homo (paso de clasificacion CASO A/B/C) y mig-version-upgrade (verificacion de compatibilidad con integra/homologado destino).
---

# verificar-referencia-modulo

Responde una sola pregunta, de solo lectura, reutilizable desde cualquier skill de migracion: **dada una referencia `modulo.external_id` (o solo `modulo` si es una dependencia de `depends`), ¿sigue siendo valida en esta ubicacion?**

No decide que hacer con el resultado -- eso depende del contexto de quien la invoca (ver "Como la consumen otras skills" al final).

## Ubicacion: dos formas equivalentes

Una ubicacion es siempre "un submodulo en un punto del tiempo". Puede expresarse de dos formas:

- **Local (working tree actual)**: una ruta tal cual esta en disco, ej. `odoo-venezuela/l10n_ve_invoice`. Se usa cuando el destino es *otro submodulo en la misma rama/checkout actual* (caso homologacion).
- **Remota (otra rama, sin checkout)**: `<submodulo>@<rama>:<ruta-dentro-del-repo>`, ej. `integra-addons@17.0:binaural_pos`. Se usa cuando el destino es *el mismo submodulo pero en otra version* (caso upgrade de version).

**Regla importante**: nunca hacer `git checkout <rama>` de un submodulo compartido solo para verificar algo -- son repos usados por muchos proyectos a la vez y un checkout deja el submodulo en un estado inesperado para el resto. Para la forma remota, leer el arbol de la rama sin tocar el working tree:

```bash
# Existe el archivo/manifest en esa rama?
git -C <submodulo> cat-file -e <rama>:<ruta> 2>/dev/null && echo EXISTE

# Buscar el external_id dentro del arbol de esa rama (sin checkout)
git -C <submodulo> grep -l "<external_id>" <rama> -- '*.xml' '*.csv' '*.py' 2>/dev/null
```

## Algoritmo

Dada una referencia `MODULO.ID` (o solo `MODULO`) y una `UBICACION`:

### Paso 1 — ¿El modulo es funcional en esa ubicacion?

"Funcional" = tiene `__manifest__.py` valido (no es un remanente vacio) en esa ubicacion.

```bash
# Local
test -f "<ubicacion>/<MODULO>/__manifest__.py" && echo FUNCIONAL || echo NO_FUNCIONAL

# Remota (rama de otro submodulo)
git -C <submodulo> cat-file -e "<rama>:<MODULO>/__manifest__.py" 2>/dev/null && echo FUNCIONAL || echo NO_FUNCIONAL
```

Si `NO_FUNCIONAL` (no existe la carpeta, o existe pero sin manifest -- remanente/dead code de una migracion anterior) → tratar como si el modulo no existiera ahi y pasar directo a **HUERFANO**, salvo que el Paso 2 encuentre el ID en otro modulo de la misma ubicacion (ver RENOMBRADO).

### Paso 2 — ¿El external ID especifico existe ahi?

Solo aplica si la referencia incluye un ID (no aplica a una simple dependencia de `depends`, que se resuelve solo con el Paso 1).

```bash
# Local
grep -rl "<ID>" "<ubicacion>/<MODULO>/" --include="*.xml" --include="*.csv" --include="*.py" 2>/dev/null

# Remota
git -C <submodulo> grep -l "<ID>" <rama> -- "<MODULO>/*.xml" "<MODULO>/*.csv" "<MODULO>/*.py" 2>/dev/null
```

- Si el modulo es FUNCIONAL (Paso 1) y el ID aparece → **FUNCIONAL**.
- Si el modulo es FUNCIONAL pero el ID no aparece dentro de el → buscar el mismo ID en el resto de la ubicacion (no solo en `<MODULO>/`), y tambien variantes de nombre conocidas (sufijo del modulo cambiado, ej. `_binaural_x` → `_l10n_ve_x`, o el mismo sufijo sin cambios si es un cambio de version). Si aparece en otro lado dentro de la misma ubicacion → **RENOMBRADO** (reportar el candidato encontrado, archivo y linea). Si no aparece en ningun lado → **HUERFANO**.
- Si el modulo es NO_FUNCIONAL → repetir la misma busqueda de variantes en toda la ubicacion antes de concluir; si no aparece nada → **HUERFANO**.

### Paso 3 — ¿Es codigo muerto? (chequeo aparte, no reemplaza el veredicto anterior)

Si el archivo que **contiene la referencia que se esta verificando** (no el destino, sino el archivo de origen que la invoca) no esta declarado en los `assets` del `__manifest__.py` de su propio modulo, marcar adicionalmente **CODIGO_MUERTO** -- es informativo para que quien invoca decida si vale la pena seguir con la migracion de esa referencia o simplemente eliminar el archivo.

## Veredictos (vocabulario estandar)

| Veredicto | Significado |
|---|---|
| **FUNCIONAL** | El modulo+ID existen tal cual en la ubicacion verificada. |
| **RENOMBRADO** | No existe con el mismo nombre, pero se encontro un candidato razonable en la misma ubicacion (reportar candidato: modulo, ID, archivo, linea). Quien invoca decide si lo adopta. |
| **HUERFANO** | No se encontro el modulo ni el ID en la ubicacion, ni ningun candidato razonable. |
| **CODIGO_MUERTO** | (adicional, no excluyente) El archivo de origen de la referencia no esta en los assets de su propio manifest -- puede eliminarse en vez de migrarse. |

## Como la consumen otras skills

- **`mig-customs-to-homo`** (modo cross-modulo, misma rama/checkout): verifica primero `integra-addons/<MODULO>` (ubicacion local); si el veredicto es HUERFANO ahi, verifica `odoo-venezuela/<equivalente>` (ubicacion local, usando su propia tabla de mapeo `binaural_*`→`l10n_ve_*` para derivar `<equivalente>`). Interpretacion: FUNCIONAL en integra-addons → CASO A (conservar); HUERFANO en integra-addons pero FUNCIONAL/RENOMBRADO en odoo-venezuela → CASO B (migrar); HUERFANO en ambas → CASO C (huerfana).
- **`mig-version-upgrade`** (modo cross-version, mismo submodulo): una sola verificacion contra `<submodulo>@<rama_destino>:<MODULO>.<ID>` (ubicacion remota). Interpretacion: FUNCIONAL → ✅ Compatible; RENOMBRADO → ⚠️ actualizar referencia al candidato reportado; HUERFANO → ❌ Bloqueante (integra/homologado destino no tiene el modulo migrado todavia a esa version).

Cada skill que invoca esto es responsable de su propia tabla de mapeo de nombres (si aplica) y de decidir la accion final -- esta skill solo entrega el veredicto y la evidencia (comandos y resultados usados) para justificarlo.
