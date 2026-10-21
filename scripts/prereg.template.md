# Pre-registro — <cambio> (congelar ANTES de despachar)

- Fecha / ronda: <YYYY-MM-DD> / <n>
- Tareas (qué se pide, `allowed_files`): <...>
- Rúbrica de aceptación (evidencia canónica = archivo o fila de log escrita por el runner, nunca prosa): <...>
- Presupuestos (tokens/tiempo/iteraciones R5): <...>
- Entorno hasheado (sdd-guardrails.json, agente, opencode.json): <sha256 de cada uno>
- Canario de cadena previo: `bash scripts/sdd_canary.sh <job_canario>` → <ok|FAIL>; si FAIL, no se expande.
- Límites declarados: <1 modelo, 1 fixture, N repeticiones — sin garantía de generalidad>

Cambiar la rúbrica o los presupuestos a mitad de ronda = ronda nueva (la anterior se conserva etiquetada).
