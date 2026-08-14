---
name: branch-create
description: Crea una rama nueva siguiendo la convencion corporativa de nombres (origen_tipo-asignacion_id_nombre-en-ingles) documentada en el PDF "Git - Ramas y Commits". Usar cuando el usuario pida crear una rama nueva, empezar un ticket/tarea, o pregunte por el formato de nombres de rama.
---

# branch-create

Crea una rama nueva en cualquier repositorio de este proyecto (repo principal `docker-odoo`, cualquier custom bajo `src/custom/*`, o los submodulos `odoo-venezuela`/`integra-addons`/`third-party-addons`) siguiendo la convencion corporativa de nombres.

Es el primer paso del flujo completo **Rama -> Commit -> PR**. Ver la skill `git-flow` para ejecutar los 3 pasos en orden. Para el paso de commit ver la skill `commit-message`, y para el paso de PR ver la skill `pr-create`.

## Convencion de nombres

```
<origen>_<tipo>-<tipo_asignacion>_<id_ticket_o_tarea>_<nombre_corto_en_ingles>
```

### Componentes

1. **origen** — de donde parte la rama. En la practica de este proyecto casi siempre es el nombre de una rama de staging/mantenimiento ya existente, pero tambien puede ser:
   - `rls` — parte del release del cliente
   - `stg` — parte del staging del cliente
   - `<hash-corto>` — parte de un commit especifico
   - `17.0`, `l10nve_17.0`, etc. — parte de una rama oficial de odoo-venezuela/integra-addons
   - `maint_17.0.1`, `maint_l10nve_17.0.1`, etc. — parte de una rama de mantenimiento trimestral

   **Nomenclatura de ramas de mantenimiento — abreviar siempre a `maint-`:** aunque la rama base real en el remoto se llame `maintenance-17.0` (o `maintenance-19.0`, etc.), el `origen` de cualquier rama nueva creada a partir de ella **se abrevia** a `maint-17.0` / `maint-l10nve-17.0` (nunca se escribe "maintenance-17.0" completo en el nombre de la rama nueva). Esto coincide con el patron dominante en el historial real (decenas de ramas `maint-17.0_fix-ti_*`, `maint-l10nve_17.0.1_*`, etc., contra un puñado de excepciones antiguas con "maintenance-" completo que no se deben repetir). Ejemplo correcto: partiendo de `origin/maintenance-17.0`, la rama nueva es `maint-17.0_fix-ta_78845_algo`, no `maintenance-17.0_fix-ta_78845_algo`.

   **Caso especial — proyectos en migracion de version (ej. casaroda/inversiones2050 migrando a 17.0):** en estos proyectos la rama de staging generica (`stg`/`staging`) fue **sustituida** por una rama de migracion dedicada con prefijo `mg_stg_<algo>` (ej. `mg_stg_l10nve_17.0`, `mg_stg_17.0`). Esta no es "otro ejemplo mas" de origen — es un **reemplazo obligatorio** de `stg`/`staging` para ese proyecto mientras dure la migracion: cualquier rama nueva del repo principal de ese cliente debe partir de la `mg_stg_*` correspondiente, nunca de `staging` directamente. Ver el paso de verificacion en "Flujo de trabajo" para como detectar si un proyecto esta en este caso.

   **Caso submodulos (`odoo-venezuela`/`integra-addons`/`third-party-addons`):** el origen por defecto es **siempre** el hash exacto que el submodulo tiene desplegado/checkout en el entorno del cliente en el que se esta trabajando (`<hash-corto>`), nunca una rama de mantenimiento con nombre propio. Solo se parte de una rama de mantenimiento (`maint-17.0`, `maint-l10nve-17.0`, `l10nve_17.0`, etc. — ver regla de abreviacion arriba) cuando el usuario lo pide explicitamente en ese momento — nunca por defecto ni por inferencia.

2. **tipo** — uno de: `hotfix`, `fix`, `feat`, `refactor`, `deploy`, `chore`, `docs`, `test`, `style`, `add`, `remove`, `perf`, `i18n`. En la practica tambien se usa `upd` para actualizaciones de submodulos aunque no este en la lista oficial. Ver la tabla tipo-de-rama -> TAG-de-commit en la skill `commit-message` (seccion 1) para elegir el tipo coherente con lo que se va a commitear despues.

3. **tipo_asignacion** — `ti` (ticket, modulo de asistencia) o `ta` (tarea, modulo de proyectos).

4. **id** — numero del ticket o tarea.

5. **nombre_corto_en_ingles** — descripcion breve en ingles, snake_case o con guiones bajos, ej. `tax_config_views`, `foreign_residual_inconsistency`, `custom_stock_higea`.

### Ejemplos reales
- `2cd70432_fix-ti_14172_tax_config_views`
- `maint-17.0_fix-ti_13694_foreign_residual_inconsistency`
- `0fc98da1_upd-ta_75512_submodules_upd`
- `mg_stg_l10nve_17.0_add-ta_14363_custom_stock_higea`
- `stg_hotfix_pos_discount_supervisor_key` (hotfix sin ticket en un repo de cliente, partiendo de `staging`)

**El prefijo de origen es obligatorio siempre, incluso en el repo principal de un cliente** (no solo en submodulos). Un hotfix sin ticket que parte de `staging` en un repo como `higea` debe llamarse `stg_hotfix_<nombre>`, nunca solo `hotfix_<nombre>` (ese patron antiguo, ej. `hotfix_higea_pos_sale_order_merge`, quedo superado — no repetirlo en ramas nuevas).

## Informacion necesaria

1. **Repositorio destino** — *derivable*. Confirmar en que repo/submodulo se va a crear la rama (`git remote -v` para verificar).

2. **Rama base (origen)** — *preguntar si no es evidente*. Desde que rama se va a partir. Sugerir la rama actual (`git branch --show-current`) si ya parece ser una rama base oficial/staging valida; si no, preguntar. Este valor se usa tanto para el `git checkout -b` como para el prefijo `origen` del nombre.

3. **Tipo** — *proponer + confirmar*. Segun la naturaleza del trabajo a realizar (ver lista de la seccion anterior). Debe ser coherente con el TAG de commit que se usara despues.

4. **Tipo de asignacion + numero** (ti/ta + id) — *preguntar siempre que no se haya mencionado ya*.

5. **Nombre corto en ingles** — *proponer a partir del contexto de la tarea + confirmar*. Breve, en ingles, sin espacios (usar guion bajo).

## Flujo de trabajo

1. Confirmar el repositorio de trabajo (`git status`, `git remote -v`).
2. Reunir los 5 elementos de la seccion anterior; preguntar lo que falte.
3. Verificar que la rama base exista localmente o en remoto:
   ```bash
   git branch --list <rama_base>
   git ls-remote --heads origin <rama_base>
   ```
   Si no existe localmente pero si en remoto, hacer `git fetch origin <rama_base>` antes de partir de ella.

   **Antes de asumir `stg`/`staging` como origen en el repo principal de un cliente**: verificar si el proyecto esta en migracion de version, buscando una rama dedicada con prefijo `mg_stg_`:
   ```bash
   git branch -r | grep -i mg_stg
   ```
   Si aparece una que coincide con el proyecto/version en curso (ej. `mg_stg_l10nve_17.0`), esa es la rama base real — usarla en lugar de `stg`/`staging` (ver "Componentes" → "origen", caso especial de migracion). Si no aparece ninguna, `stg`/`staging` sigue siendo el origen correcto.

   **Caso submodulos (`odoo-venezuela`/`integra-addons`/`third-party-addons`) en un proyecto con migracion en curso**: estos repos son compartidos entre clientes, por lo que no tienen su propia rama `mg_stg_` — no asumir `maintenance-17.0` (u otra rama generica) como origen sin antes verificar si existe una rama de integracion especifica del cliente. Procedimiento:
   1. Obtener el hash exacto que el repo principal referencia para el submodulo en su rama `mg_stg_*`:
      ```bash
      git ls-tree origin/<rama_mg_stg_del_padre> -- <submodulo>
      ```
   2. Buscar, entre las ramas candidatas del submodulo (`git branch -r | grep -i <cliente>` o similar), cual es ancestro real de ese hash:
      ```bash
      git merge-base <hash> origin/<rama_candidata>
      ```
      Si el resultado coincide con el tip de `<rama_candidata>`, esa es la rama de integracion especifica del cliente (ej. `maint-17.0.1_mg-ta_68400_migration_casaroda`) y debe usarse como origen — en lugar de `maintenance-17.0` generico. Si ninguna candidata calza, partir directamente del hash exacto obtenido en el paso 1 (ver "Componentes" → "origen", caso `<hash-corto>`).
4. **Siempre, antes de crear la rama nueva**: verificar que la rama base local este sincronizada con `origin` (nunca partir de una base desactualizada, aunque ya exista localmente).
   ```bash
   git fetch origin <rama_base>
   git status
   ```
   Si `git status` muestra que la rama base local esta detras de `origin/<rama_base>`, actualizarla primero (`git pull` estando parado en esa rama, o el equivalente segun el caso) antes de partir de ella con `checkout -b`.

   Si el repositorio tiene submodulos (repo principal de cliente con `odoo-venezuela`/`integra-addons`/`third-party-addons`) y el fetch/pull anterior trajo cambios en los punteros de submodulo (`git status` los marca como modificados, o `git diff` en la rama base muestra cambios bajo esas carpetas), sincronizarlos antes de continuar:
   ```bash
   git submodule update --init --recursive
   ```
   Esto evita crear la rama nueva sobre una base con submodulos desactualizados o sin inicializar.
5. Construir el nombre final: `<origen>_<tipo>-<tipo_asignacion>_<id>_<nombre_ingles>`.
6. Mostrar el nombre propuesto al usuario para su aprobacion antes de crear la rama.
7. Si el usuario aprueba, crear la rama:
   ```bash
   git checkout -b <nombre_final> <rama_base>
   ```
8. **No hacer push todavia** — el push se hace en el paso de PR (ver skill `pr-create`), una vez exista al menos un commit.
   **Excepcion (submodulos, siempre):** si la rama es de un submodulo (`integra-addons`/`odoo-venezuela`/`third-party-addons`), hacer push a origin **inmediatamente despues del commit**, sin excepcion — sea cual sea el `origen` (hash de cliente, `l10nve_17.0`, `maint-*`, etc.) y sin importar si se va a crear PR o no. El puntero de submodulo en el repo del cliente referencia ese commit por SHA; si el commit no existe en el remoto del submodulo, nadie mas puede resolverlo (`git submodule update` falla al no encontrarlo). El PR del submodulo si es condicional: solo se crea cuando el cambio va a mantenimiento (ver skill `pr-create`, seccion "Submodulos: push siempre, PR solo si va a mantenimiento").
9. Confirmar con `git status` que la rama quedo creada y activa.
