---
name: pr-create
description: Hace push de la rama actual y crea el Pull Request en GitHub via gh CLI, con titulo/cuerpo derivados del commit (Resumen/Problema/Causa/Solucion + References), sin seccion de plan de pruebas. Usar cuando el usuario pida crear un PR, publicar la rama, o subir los cambios para revision.
---

# pr-create

Hace push de la rama actual a `origin` y crea el Pull Request correspondiente en GitHub usando `gh` CLI.

Es el tercer y ultimo paso del flujo completo **Rama -> Commit -> PR**. Ver la skill `git-flow` para ejecutar los 3 pasos en orden. Para crear la rama ver `branch-create`, para el commit ver `commit-message`.

**Importante**: `push` y `crear PR` son acciones que afectan estado compartido/publico (visibles para el equipo) — requieren confirmacion explicita del usuario antes de ejecutarse, incluso dentro de este flujo. Nunca asumir aprobacion de un paso anterior como aprobacion para este.

## Precondiciones: `gh` CLI

Antes de intentar crear el PR, verificar:

```bash
gh --version
gh auth status
```

- Si `gh` no esta instalado: proponer instalarlo. En Ubuntu/Debian suele estar disponible directo en el repo `universe` (`apt-cache policy gh` para confirmar) sin necesidad de agregar el repositorio oficial de GitHub. **Nunca ejecutar `sudo` por el usuario** — `sudo` requiere una contrasena interactiva que este agente no puede proveer. Dar el comando exacto (`sudo apt update && sudo apt install -y gh`) para que el usuario lo corra en su propia terminal.
- Si `gh` esta instalado pero no autenticado (`gh auth status` falla): **nunca ejecutar `gh auth login` por el usuario**. Es un flujo interactivo (device flow: pide elegir host/protocolo y despues muestra un codigo de un solo uso para pegar en `https://github.com/login/device`) que no funciona bien lanzado como proceso en segundo plano por el agente. Dar el comando exacto para que el usuario lo corra en su propia terminal, y esperar a que confirme que quedo logueado antes de continuar.
- Una vez confirmado `gh auth status` exitoso, continuar con el flujo normal.

## Submodulos: push siempre, PR solo si va a mantenimiento

Regla general para cualquier rama de submodulo (`integra-addons`/`odoo-venezuela`/`third-party-addons`), sin excepcion:

- **Push: siempre.** Apenas exista el commit, hacer `git push -u origin <rama-submodulo>` a origin, sin esperar al paso de PR y sin condicionarlo a si se va a crear PR o no. El repo principal del cliente (ej. `higea`) referencia el commit del submodulo por SHA en su puntero; si ese commit solo existe localmente, cualquier otra persona o sistema que clone/actualice el repo principal y corra `git submodule update` no podra resolverlo. Esto aplica igual para una rama basada en un hash especifico de cliente (ver `branch-create`, convencion de `origen` = `<hash-corto>`) que para una rama basada en `l10nve_17.0`/`maint-*`.

- **PR: solo si el cambio va a mantenimiento.** Crear PR en el submodulo unicamente cuando el fix/feature ya esta validado y se va a integrar a una rama de mantenimiento compartida entre clientes (`l10nve_17.0`, `maint-l10n-17.0.x`, etc.). Si el cambio todavia esta en fase de prueba puntual en el ambiente de un solo cliente (rama basada en el hash de ese cliente), **no se crea PR en el submodulo todavia** — se deja la rama pusheada, y el PR del submodulo se hace en una iteracion posterior, cuando el usuario decida subirlo a mantenimiento. Preguntar siempre al usuario en cual de los dos casos esta antes de decidir si se crea el PR del submodulo.

En cualquiera de los dos casos, el push nunca se omite — lo unico condicional es el PR.

## Informacion necesaria

1. **Rama actual y su estado** — *derivable*. `git branch --show-current`, `git log` para confirmar que hay al menos un commit no pusheado.

2. **Rama base (target del PR)** — *derivable (proponer) + confirmar*. Intentar inferirla buscando, entre las ramas locales/remotas existentes, la que sea prefijo literal del nombre de la rama actual (el componente `origen` de la convencion de `branch-create`). Ejemplo: si la rama actual es `mg_stg_l10n_ve_17.0_add-ta_14363_custom_stock_higea`, buscar si existe `mg_stg_l10n_ve_17.0` como rama y proponerla como base. Si no se puede inferir con confianza, preguntar.

3. **Titulo del PR** — *derivable*. Reusar la primera linea del commit (`[TAG] módulo(s): descripción corta`) via `git log -1 --format=%s`, salvo que el usuario pida uno distinto.

4. **Cuerpo del PR** — *derivable del commit + conversacion*. A diferencia del mensaje de commit (que NO usa encabezados literales, ver skill `commit-message`), el cuerpo del PR SI usa encabezados Markdown porque GitHub los renderiza bien:

   ```markdown
   ## Resumen
   <que se hizo, 1-2 lineas>

   ## Problema
   <cual era el error/comportamiento incorrecto, o el contexto/motivo si no aplica un error (FEAT/ADD/CHORE)>

   ## Causa
   <causa raiz tecnica — omitir esta seccion si no aplica (ej. FEAT sin bug asociado)>

   ## Solucion
   <como se resolvio tecnicamente>

   References:
   - Ticket: <URL completa o vacío>
   - Tarea: <URL completa o vacío>
   ```

   **No incluir seccion de "Test plan" ni checklist de pruebas** — el usuario indico explicitamente que no hace falta.

   Si el commit ya tiene la informacion (Resumen/Problema/Causa/Solucion en prosa, ver `commit-message`), reformatear esas mismas ideas con encabezados Markdown en vez de redactar contenido nuevo desde cero.

5. **Confirmacion final** — *preguntar siempre*. Mostrar titulo + cuerpo propuestos antes de ejecutar `gh pr create`.

## Flujo de trabajo

1. Verificar precondiciones de `gh` (seccion anterior).
2. Confirmar que la rama actual tiene commits pendientes de push:
   ```bash
   git status
   git log @{u}.. 2>/dev/null || git log -1
   ```
3. Determinar rama base (inferir + confirmar con el usuario).
4. Construir titulo y cuerpo del PR (seccion "Informacion necesaria").
5. Mostrar el borrador completo (titulo + cuerpo + rama base) al usuario y esperar aprobacion explicita.
6. Si el usuario aprueba:
   ```bash
   git push -u origin <rama_actual>
   gh pr create --base <rama_base> --head <rama_actual> --title "<titulo>" --body "<cuerpo>"
   ```
7. Devolver la URL del PR creado al usuario.

## Ejemplo real (PR creado para higea_stock_account, Ticket 14363)

```markdown
## Resumen
Se crea el modulo `higea_stock_account`, adaptado desde `grupokam_stock_account` para higea, corrigiendo en el proceso un bug de `l10n_ve_stock_account`.

## Problema
Al cambiar el motivo de traslado de una guia a uno que no requiere guia de despacho (ej. traslado entre almacenes), el campo `is_dispatch_guide` se quedaba en `True`, forzando `partner_id` como obligatorio en la vista y bloqueando la validacion de traslados internos entre almacenes.

## Causa
`_compute_is_dispatch_guide` en `l10n_ve_stock_account` es un campo `store=True` cuyo compute no cubre con un `else` explicito el caso de motivos que no requieren guia, por lo que el campo conservaba el ultimo valor calculado en vez de resetearse a `False`.

## Solucion
Se sobrescribe unicamente `_compute_is_dispatch_guide` en `higea_stock_account`, reasignando el valor en cada calculo sin dejar ninguna rama sin cubrir, sin tocar el `store` del campo para no afectar la vista ni los campos dependientes (`match_guide_dispatch_domain`).

References:
- Ticket: https://binaural.odoo.com/odoo/my-tickets/14363
```
