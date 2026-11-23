# Tareas (completadas 2026-08-15)

- [x] Encontrar la causa raíz leyendo el código de arranque (no solo el
      síntoma reportado): `.resources/entrypoint.d/600-wait-postgress` usa
      recursión por subshells en vez de un loop.
- [x] Reescribir con `until ... do ... done` (loop real, sin acumular
      procesos) y un timeout configurable (`WAIT_PG_TIMEOUT`, default 300s).
- [x] Revisar `.resources/wait-for-psql.py` (el otro script de espera) —
      confirmado que ya usaba un loop acotado, no tenía este problema.
- [x] Validar con un binario `psql` simulado que siempre falla: confirma
      timeout limpio, `exit 1`, mensaje de error claro, sin procesos
      colgados.
- [x] Verificar sintaxis del script (`bash -n`) y permisos de ejecución
      (`chmod +x`).
