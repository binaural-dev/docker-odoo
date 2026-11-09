# MIGRATION_PLAN — `fleet_inspection` 18.0.1.0.0 → 18.0.1.1.0 en producción

Plan para actualizar la base de producción de un cliente. Está escrito para que lo ejecute otra persona sin
consultar. Lo que va entre `<…>` se reemplaza por los datos reales de la instancia.

| | |
|---|---|
| Cambio | El tipo de vehículo de las inspecciones pasa de campo de selección (`vehicle_type`) a catálogo (`vehicle_type_id` → `fleet.inspection.vehicle.type`) |
| Módulo que se actualiza | **solo `fleet_inspection`** |
| Script | `migrations/18.0.1.1.0/pre-migrate.py` y `post-migrate.py` (lógica en `migration_utils.py`) |
| Duración medida de la actualización | 10.000 inspecciones: **~4,6 s** el `-u` completo · 100.000: **~9,5 s** (ver «Mediciones») |
| Ventana recomendada | 30 minutos fuera del horario de uso (incluye respaldo y verificaciones) |
| Riesgo | Bajo: la actualización es una sola transacción. Si el script falla, Odoo deshace todo y la base queda como estaba |
| Personas | Ejecuta: `<responsable técnico>` · Valida con el cliente: `<consultor>` · Decide la reversión: `<líder técnico>` |

## 0. Antes del día de la ventana

1. **Ensayo en staging con una copia de producción** (obligatorio). Se restaura el último respaldo de
   producción en una base de staging, se siguen los pasos 2 a 5 de este plan y se anotan los conteos y los
   tiempos. Si algo no coincide, la ventana no se hace.
2. Confirmar con el cliente la ventana y avisar a los usuarios: «Inspecciones no estará disponible de
   `<hora>` a `<hora>`».
3. Confirmar que el código a desplegar es la etiqueta o commit aprobado (`<tag/commit>`), con
   `fleet_inspection` en versión **18.0.1.1.0**.

## 1. Respaldo

```bash
# Base de datos + filestore en un ZIP (script del repositorio)
./scripts/odoo_backup backup <instancia> -d <base> -p /respaldos/fleet_inspection_<AAAAMMDD>
```

- Verificar que el ZIP existe, que su tamaño es razonable (similar al último respaldo) y anotar la ruta.
- **Comprobar que el respaldo se puede restaurar**: el ensayo de staging del paso 0 se hace con este mismo
  procedimiento. Un respaldo que nunca se restauró no cuenta como respaldo.

## 2. Verificación previa

Conectarse a la base (`./odoo psql <instancia> -d <base>`) y **guardar la salida** de cada consulta: se compara
en el paso 4.

```sql
-- 2.1 Versión instalada: debe ser 18.0.1.0.0 y estado installed
SELECT latest_version, state FROM ir_module_module WHERE name = 'fleet_inspection';

-- 2.2 Inspecciones por tipo (GUARDAR: es la referencia para verificar)
SELECT vehicle_type, count(*) FROM fleet_inspection GROUP BY 1 ORDER BY 1;

-- 2.3 Total de inspecciones (GUARDAR)
SELECT count(*) FROM fleet_inspection;

-- 2.4 Valores fuera de la selección conocida (moto, carro, camión, otro).
--     No bloquea: el script los crea como tipos nuevos. Anotarlos para avisar al cliente.
SELECT vehicle_type, count(*) FROM fleet_inspection
 WHERE vehicle_type NOT IN ('motorcycle', 'car', 'truck', 'other') GROUP BY 1;

-- 2.5 Inspecciones sin tipo: debe ser 0 (el campo era obligatorio). Si no es 0: NO SEGUIR (ver «Criterios»)
SELECT count(*) FROM fleet_inspection WHERE vehicle_type IS NULL;

-- 2.6 Ningún otro módulo pendiente de actualizar: debe devolver 0 filas
SELECT name, state FROM ir_module_module WHERE state IN ('to upgrade', 'to install', 'to remove');

-- 2.7 Que no exista ya la columna de respaldo de un intento anterior: debe devolver 0 filas.
--     Si existe, el script la reutiliza (es idempotente); anotarlo igual.
SELECT column_name FROM information_schema.columns
 WHERE table_name = 'fleet_inspection' AND column_name = 'legacy_vehicle_type';
```

**Criterios para seguir (go/no-go):** 2.1 en `18.0.1.0.0`/`installed`, 2.5 = 0, 2.6 sin filas y respaldo
verificado. Si alguno falla, se suspende la ventana y se avisa al cliente.

## 3. Ejecución

```bash
# 3.1 Cerrar el acceso de los usuarios: detener el proxy por el que entran (la instancia sigue arriba,
#     porque ./odoo update corre Odoo DENTRO de su contenedor, en otro puerto)
docker compose -f docker-compose.generated.yml stop nginx

# 3.2 Desplegar el código aprobado
cd src/custom/<proyecto> && git fetch && git checkout <tag/commit> && cd -

# 3.3 Actualizar SOLO fleet_inspection, guardando el registro
./odoo update <instancia> -d <base> -m fleet_inspection 2>&1 | tee /respaldos/fleet_inspection_<AAAAMMDD>/upgrade.log

# 3.4 Reiniciar la instancia para que sus procesos carguen el código nuevo, y reabrir el acceso
./odoo restart <instancia>
docker compose -f docker-compose.generated.yml start nginx
```

> Si el cliente entra directo al puerto de la instancia y no por el proxy, en 3.1 hay que bloquear ese
> puerto en el firewall del servidor. No se detiene la instancia: `./odoo update` la necesita levantada.

En el registro (`upgrade.log`) deben aparecer, en este orden:

```
module fleet_inspection: Running upgrade [>18.0.1.1.0] pre-migrate
fleet_inspection: <N> inspecciones respaldadas en legacy_vehicle_type (<L> lotes, <s> s, memoria máx. <M> MB)
module fleet_inspection: Running upgrade [18.0.1.1.0>] post-migrate
fleet_inspection: <N> inspecciones con tipo asignado (<L> lotes, <s> s, memoria máx. <M> MB); tipos creados: <...>
```

- `<N>` debe ser igual al total de 2.3.
- «tipos creados» debe coincidir con los valores de 2.4 (o decir «ninguno»). Cada uno aparece además como
  `WARNING ... fuera del catálogo; se creó como tipo nuevo`; es esperado.
- Si aparece `RuntimeError: ... quedaron sin tipo de vehículo; se aborta la actualización` o cualquier
  `ERROR`/`CRITICAL`: **la actualización no se aplicó** (Odoo deshace todo) → ir a «Reversión, caso A».

## 4. Verificación posterior

```sql
-- 4.1 Versión: debe ser 18.0.1.1.0
SELECT latest_version, state FROM ir_module_module WHERE name = 'fleet_inspection';

-- 4.2 Inspecciones por tipo: debe coincidir EXACTAMENTE con 2.2 (código = valor anterior)
SELECT t.code, count(*) FROM fleet_inspection i
  JOIN fleet_inspection_vehicle_type t ON t.id = i.vehicle_type_id GROUP BY 1 ORDER BY 1;

-- 4.3 Total: igual a 2.3
SELECT count(*) FROM fleet_inspection;

-- 4.4 Sin tipo: debe ser 0
SELECT count(*) FROM fleet_inspection WHERE vehicle_type_id IS NULL;

-- 4.5 Tipo distinto al valor original: debe ser 0
SELECT count(*) FROM fleet_inspection i
  JOIN fleet_inspection_vehicle_type t ON t.id = i.vehicle_type_id
 WHERE t.code <> i.legacy_vehicle_type;

-- 4.6 La base exige el tipo (NOT NULL): debe decir NO
SELECT is_nullable FROM information_schema.columns
 WHERE table_name = 'fleet_inspection' AND column_name = 'vehicle_type_id';
```

En la interfaz, con un usuario supervisor:

1. *Flota › Inspecciones*, agrupar por *Tipo de vehículo*: los grupos y cantidades coinciden con 2.2.
2. Abrir una inspección de cada tipo, incluida una de «Otro»: muestra su tipo.
3. Crear una inspección nueva: el tipo por defecto es «Carro»; guardarla y borrarla (en borrador).
4. *Imprimir › Inspección* de una inspección existente: el PDF muestra el tipo.
5. *Flota › Configuración › Tipos de vehículo (inspecciones)*: están los 4 tipos más los de 2.4.

Si todo coincide: avisar al cliente que el sistema está disponible y **conservar el respaldo al menos 30
días**. La columna `legacy_vehicle_type` se deja en la base como respaldo: se puede eliminar en una versión
futura, cuando el cliente confirme que todo está bien.

## 5. Reversión

### Caso A — la actualización falló (paso 3) o la verificación falló antes de abrir a los usuarios

Si el `-u` abortó, la base no cambió: Odoo deshace toda la transacción.

1. Mantener cerrado el acceso de los usuarios (proxy detenido, paso 3.1).
2. Volver al código anterior: `git checkout <tag/commit de la 18.0.1.0.0>`.
3. Si el `-u` terminó pero la verificación (paso 4) falló, restaurar el respaldo del paso 1:
   `./odoo restore <instancia> -z /respaldos/fleet_inspection_<AAAAMMDD>/<archivo>.zip -d <base>`
4. `./odoo restart <instancia>` y repetir la verificación 2.1 a 2.3: los resultados deben ser los guardados.
5. Reabrir el acceso (`docker compose -f docker-compose.generated.yml start nginx`), avisar al cliente y
   analizar el `upgrade.log` antes de reprogramar.

### Caso B — se detecta un problema después de abrir a los usuarios

Restaurar el respaldo perdería lo cargado desde la ventana. En ese caso se devuelve la base a la 18.0.1.0.0
reconstruyendo la selección desde los datos actuales.

**Se ensaya primero en staging, con una copia del estado actual.**

```sql
-- B.1 Recrear la columna de la selección con el código del tipo actual de cada inspección
--     (incluye las creadas después de la migración)
ALTER TABLE fleet_inspection ADD COLUMN IF NOT EXISTS vehicle_type varchar;
UPDATE fleet_inspection i SET vehicle_type = t.code
  FROM fleet_inspection_vehicle_type t WHERE t.id = i.vehicle_type_id;

-- B.2 Comprobar: 0 inspecciones sin valor
SELECT count(*) FROM fleet_inspection WHERE vehicle_type IS NULL;

-- B.3 Marcar el módulo en la versión anterior para que Odoo lo vuelva a cargar con el código viejo
UPDATE ir_module_module SET latest_version = '18.0.1.0.0' WHERE name = 'fleet_inspection';
```

Luego, con el acceso de los usuarios cerrado (paso 3.1):
1. `git checkout <tag/commit de la 18.0.1.0.0>`.
2. `./odoo update <instancia> -d <base> -m fleet_inspection`. El código viejo vuelve a usar `vehicle_type` y
   Odoo elimina la columna `vehicle_type_id`. La tabla `fleet_inspection_vehicle_type` queda en la base sin
   uso, porque Odoo no borra las tablas de modelos eliminados. No molesta, y si se vuelve a migrar, los tipos
   se reutilizan por código.
3. `./odoo restart <instancia>`.
4. Verificar con las consultas 2.1 a 2.3 y reabrir el acceso.

**Ensayado** sobre una copia ya migrada de la base de 10.000 inspecciones. Después del `-u` con el código de la
18.0.1.0.0: versión 18.0.1.0.0, 0 errores en el registro, y los mismos conteos por tipo que antes de la
migración (car 4466 · motorcycle 2553 · other 994 · trailer 10 · truck 1977, total 10.000).

Limitación: un tipo creado a mano en el catálogo después de la migración no existe en la selección de la
18.0.1.0.0. La consulta B.1 conserva su código, pero el código viejo solo conoce moto, carro, camión y otro.
Antes de revertir, revisar si hay tipos nuevos en uso y acordar con el cliente a cuál de los 4 se pasan.

## Mediciones

**Cómo se generaron los datos.** `scripts/generate_inspections.py` crea inspecciones con el ORM (cada una con
su checklist de 5 puntos), en lotes de 1.000, con semilla fija (25 % moto, 45 % carro, 20 % camión, 10 % otro).
Agrega además 10 con un valor fuera de la selección («trailer») vía SQL, para simular datos heredados.

```bash
# Sobre una base con fleet_inspection 18.0.1.0.0
TOTAL=10000 odoo shell -c <odoo.conf> -d <base> --no-http < scripts/generate_inspections.py
```

| Datos generados | Tiempo de generación | Tamaño de la base |
|---|---|---|
| 10.000 inspecciones + 50.000 líneas de checklist | 14,5 s | 42 MB |
| 100.000 inspecciones + 500.000 líneas de checklist | 147,0 s | 136 MB |

**Cómo se midió.** Cada corrida parte de una copia limpia de la base (`createdb -T <plantilla>`) y ejecuta
`odoo -d <copia> -u fleet_inspection --stop-after-init`.
- **`-u` completo:** tiempo de reloj del comando, que incluye cargar Odoo, actualizar el módulo y los dos scripts.
- **Respaldo y asignación:** tiempos que escribe el propio script en el registro (`time.perf_counter`).
- **Memoria:** el máximo de memoria residente del proceso de Odoo (`resource.getrusage`, `ru_maxrss`), escrito
  por el script al terminar cada paso.

Equipo: AMD Ryzen 7 3700X (16 hilos visibles en WSL2), 7 GB para WSL2, Docker Desktop, PostgreSQL 16.15 y
Odoo 18.0 en contenedores, en una laptop de desarrollo (no un servidor).

| Inspecciones | Corrida | `-u` completo | Respaldo (pre) | Asignación (post) | Lotes por paso | Memoria máx. del proceso |
|---|---|---|---|---|---|---|
| 10.000 | 1 | 4,66 s | 0,10 s | 0,43 s | 10 | 133 MB |
| 10.000 | 2 | 4,50 s | 0,11 s | 0,38 s | 10 | 133 MB |
| 10.000 | 3 | 4,53 s | 0,11 s | 0,39 s | 10 | 133 MB |
| 100.000 | 1 | 9,64 s | 1,17 s | 4,16 s | 100 | 134 MB |
| 100.000 | 2 | 9,46 s | 1,19 s | 3,95 s | 100 | 133 MB |

En todas las corridas, después de actualizar: conteos por tipo idénticos a los de antes (incluidos los 10
«trailer», creados como tipo nuevo), 0 sin tipo, 0 con un tipo distinto al original y `NOT NULL` aplicado.

**Lo que muestran los números:**

- **La memoria no crece con el volumen:** 133 MB con 10.000 y con 100.000. Ninguna inspección pasa por
  Python; solo los ids del lote (como máximo 1.000).
- **El tiempo crece en proporción al volumen:** 10 veces más inspecciones tardan unas 10 veces más en la
  asignación (0,4 s → 4,0 s). La mayor parte del `-u` es el arranque de Odoo.
- **Una mejora que salió de medir.** La primera versión por lotes buscaba en cada lote «las siguientes filas
  pendientes» desde el principio de la tabla. Con 100.000 inspecciones tardaba 2,41 s en el respaldo y
  5,84 s en la asignación (13,0 s el `-u`): 15 veces más que con 10.000, no 10. Se cambió a recorrer la tabla
  por id desde el último lote (paginación por clave), que dio los números de la tabla.

**Qué significan los lotes y qué no.** La actualización de un módulo en Odoo es **una sola transacción**: si
algo falla, se deshace todo, y eso se quiere conservar. Los lotes no hacen *commits* parciales. Acotan el
tamaño de cada sentencia, mantienen la memoria constante y dejan el avance en el registro. Por ser
idempotente, si la actualización se corta, al repetirla el script retoma desde cero sin duplicar nada.
