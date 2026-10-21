# Diagnostico previo al re-dispatch (copiar a src/specs/<cambio>/diagnosis-<job_id>.md)

Se escribe ANTES de volver a despachar tras un fallo. El Context {} del re-dispatch lleva
`retry_of: <job_id>` y `diagnosis_path: <esta ruta>`. Despues del diagnostico, registrar el error:
`python3 scripts/sdd_error_report.py add --job <job_id> --role <rol> --class <clase> --symptom "..." --root-cause "..." --fix "..."`

## sintoma
Que se observo exactamente (mensaje de error, exit code, paso donde se detuvo). Sin interpretar.

## evidencia
archivo:linea, extracto de `output.log`/`result.handoff`, comando que lo reproduce.

## causa_raiz
Por que ocurrio (la causa, no el sintoma). Si es hipotesis, decir como se confirmo o que falta confirmar.

## descartado
Causas probadas y descartadas, con la prueba. Evita que el agente repita la misma pista.

## fix_sugerido
Que cambiar y donde (archivo:linea), y como verificar que quedo resuelto.

Clase del error (`sdd_error_report.py`): infra | context | guardrail | spec | code | test | tooling | misread.
