# Pre-registro — <cambio> (congelar ANTES de despachar)

- Fecha / ronda: <YYYY-MM-DD> / <n>
- Tareas (qué se pide, `allowed_files`): <...>
- Rúbrica de aceptación (evidencia canónica = archivo o fila de log escrita por el runner, nunca prosa): <...>
- Presupuestos (tokens/tiempo/iteraciones R5): <...>
- Entorno hasheado (sdd-guardrails.json, agente, opencode.json): <sha256 de cada uno>
- Canario de cadena previo: `bash scripts/sdd_canary.sh <job_canario>` → <ok|FAIL>; si FAIL, no se expande.
- Límites declarados: <1 modelo, 1 fixture, N repeticiones — sin garantía de generalidad>

Cambiar la rúbrica o los presupuestos a mitad de ronda = ronda nueva (la anterior se conserva etiquetada).

## Si la ronda compara una regla inyectada (p. ej. `lean: on|off`, plugin `sdd-lean-ruleset.js`)
- Brazos y tareas: <misma spec y `spec_sha256` en ambos brazos; orden de ejecución sorteado>
- Métricas (de archivos/logs, no prosa): líneas del diff (`git diff --shortstat`), tokens (`opencode stats`), rondas hasta PASS, clases de error (`sdd_error_report.py top`), nº de tests y cobertura.
- Regla de adopción fijada de antemano: <p. ej. líneas o tokens −15 % o más SIN bajar tasa de PASS, nº de tests ni cobertura>; N pequeño: se reportan cifras crudas, sin afirmar significancia.
