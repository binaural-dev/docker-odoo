# Cobertura de tests por módulo — línea base y barridos

## Qué hay acá

| Archivo | Qué es |
|---|---|
| `baseline-2026-08.json` | Línea base de la medición del **6–7 de agosto de 2026**, extraída del informe que circuló como artifact. Es la referencia contra la que se calcula el progreso. |
| `artifact-2026-08.html` | Copia del informe de agosto tal cual se publicó (el JSON va embebido en la línea 433). |
| `dataset-<fecha>.json` | Dataset de cada barrido nuevo, producido por `scripts/coverage-sweep-aggregate`. |

## Procedencia de la línea base

El informe de agosto lo produjo un agente en la nube. **Su orquestador no existe en
ninguna máquina local**: se buscó por nombre y por contenido en todo el home (incluidos
`deliverables/`, `.claude/`, scratchpads y transcripciones de sesiones) y no hay script
de barrido, ni JSON crudo, ni logs. Lo único que sobrevivió fue el HTML del artifact.

Por eso el JSON está commiteado acá: antes vivía únicamente dentro de ese HTML en la nube
y de un `tool-results/` de sesión que se poda. Si se pierde el enlace, se pierde la
referencia.

Se extrajo así:

```bash
python3 - <<'PY'
import json, re
line = open('artifact-2026-08.html', encoding='utf8').read().split('\n')[432]
data = json.loads(re.match(r'\s*const DATA = (\{.*\});\s*$', line).group(1))
PY
```

## Qué midió agosto

Cada módulo instalado en **su propia base**, clonada de una plantilla con
`base, web, mail, contacts, account, product, stock, sale, purchase` ya instalados, y su
suite corrida con `--test-tags=/<módulo>` para que no la infle ningún test ajeno.
`coverage.py` con `--source` limitado al directorio del módulo, sin datos de demo y con un
solo worker.

|  | 17.0 | 19.0 |
|---|---|---|
| Módulos medidos | 202 (36 ov + 166 integra) | 175 (38 ov + 137 integra) |
| Excluidos por dependencias | 0 | 18 |
| Cobertura ponderada | 63,4 % | 77,3 % |
| Con archivos de test | 49 | 75 |
| No instalan | 8 | 12 |
| Duración | 9,8 h | 10,2 h |

Refs: integra `17.0.2.1.1-beta.6` (`1845609c4`) y ov `17.0.2.0.6-beta.7` (`7362feac`),
ambos en `maintenance-17.0`; integra `19.0.3.9.0-alpha.11` (`9d24d5f33`) y ov
`19.0.3.3.4-alpha.13` (`06268f0e`) en HEAD desprendido.

## Aritmética (re-derivada contra este dataset — no improvisar)

`pct` es **inclusivo de ramas** (`.coveragerc` tiene `branch = True`), mientras
`stmts`/`miss` son solo de líneas. Con la fórmula de solo líneas, 266 de 377 filas de
agosto no cuadran; con esta, cuadran.

```python
pct   = round(cov["totals"]["percent_covered"])
stmts = cov["totals"]["num_statements"]
miss  = stmts - cov["totals"]["covered_lines"]

# el orden importa: sin_codigo se evalúa ANTES que pct
if error:                                             klass = "error"
elif stmts < 3:                                       klass = "sin_codigo"
elif pct > 0:     klass = "con_tests" if has_tests else "sin_tests"
elif install_state and install_state != "installed":  klass = "no_instala"
else:                                                 klass = "cero"
```

Agregados, sobre los módulos sin `error`: `avg_pct = round(mean(pct), 1)`;
`weighted_pct = round((Σstmts − Σmiss)/Σstmts*100, 1)`; `zero = pct == 0`; los tramos
`low`/`mid`/`high` son `0<pct<30` / `30<=pct<=70` / `pct>70` y **los de 0 % no entran en
ninguno**. `install_state`/`install_cause` son no nulos solo para `no_instala` y `cero`.

## Comparabilidad con los barridos nuevos

**Esta línea base queda como archivo histórico: no se usa para calcular
progreso.** El motivo es de método, y conviene tenerlo escrito para que nadie
arme la comparación por su cuenta creyendo que cuadra.

La medición de agosto contó dentro de la cobertura los archivos de test, los
`__init__.py` y los `__manifest__.py`; el `omit` del `.coveragerc` no llegó a
aplicarse en esa corrida (`coverage json` toma el rcfile del directorio de
trabajo, y ahí no lo encontró). Los barridos nuevos sí lo aplican, que es el
criterio que declara el `.coveragerc` del repo.

Como los archivos de test se ejecutan casi al 100 %, incluirlos sube el
porcentaje. Reproducido sobre `binaural_rate`, con el árbol del módulo
byte-idéntico al commit de agosto (`1845609c4`):

| | pct | stmts | miss |
|---|---|---|---|
| contando tests y boilerplate (agosto) | 63 % | 133 | 38 |
| sin contarlos (barridos nuevos) | 42 % | 75 | 36 |

Los 133 se descomponen exacto: 75 de los cuatro modelos + 51 del archivo de
test + 1 de `tests/__init__.py` + 1 + 4 de los `__init__.py` + 1 del manifest.

Un delta entre las dos mediciones mide sobre todo ese cambio de criterio, no
trabajo de pruebas. Para tener un progreso real habría que **re-medir los
commits de agosto con el método nuevo** — los commits están en los clones, así
que es posible cuando haga falta.

Lo que la línea base sí sigue sirviendo:

- **Validar la aritmética.** `coverage-sweep-aggregate --selftest` recalcula sus
  agregados desde sus propios módulos y los compara con los guardados. Eso
  verifica las fórmulas y la precedencia de `klass`, que son independientes del
  criterio de exclusión.
- **Elegir casos de prueba** con clasificación conocida al armar un piloto.
