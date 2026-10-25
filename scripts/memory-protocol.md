# Protocolo de memoria persistente (Engram)

Tienes acceso a una memoria local compartida con Claude y OpenCode. Úsala así:

1. Antes de decidir algo, busca lo ya decidido: `mem_search` con el ticket, el módulo o la palabra clave
   sin acentos. Desde otro repositorio añade `all_projects: true`, o la búsqueda no ve las lecciones del
   proyecto `docker-odoo`. Si un resultado te interesa, pide el detalle con `mem_get_observation`.
2. Guarda solo lo que otro agente o una sesión futura necesita: decisiones con su motivo, descubrimientos
   del código, errores y su causa raíz, y el estado al cerrar una tarea.
3. Usa `topic_key` con esta forma: `sdd/<ticket|módulo>/<fase>`, `decision/<módulo>/<slug>`,
   `error/<fingerprint>`. Repetir una clave actualiza la observación en vez de duplicarla.
4. Al empezar, abre tu sesión con `mem_session_start` (id propio, p. ej. `opencode-<módulo>-<hora>`) y pasa ese
   mismo `session_id` en cada escritura. Sin él, la escritura falla si hay otra sesión activa en el mismo
   directorio. Al terminar, cierra con `mem_session_finalize`.
5. Título corto y específico, sin prefijo de ticket, rama ni rol: eso va en `topic_key` y en el contenido.
   Añade al final del contenido una línea `keywords:` con palabras clave en ASCII sin acentos.
   Si `mem_save` responde `judgment_required: true`, llama a `mem_judge` con el `judgment_id` de cada candidato:
   `related` si es la misma serie de trabajo, `supersedes` si reemplaza una decisión anterior, `conflicts_with`
   si la contradice. Indica el motivo.
6. No guardes secretos, contraseñas, tokens, datos de clientes ni el contenido de `<private>...</private>`.
7. No guardes diffs completos ni salidas de consola largas. Guarda la conclusión y la ruta del archivo.
8. Llama a las herramientas de una en una: espera la respuesta antes de la siguiente.
