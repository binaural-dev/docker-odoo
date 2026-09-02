# Tareas (completadas 2026-08-15)

- [x] Confirmar la causa raíz leyendo `get_databases()` (`odoo:395`), no solo
      el síntoma reportado.
- [x] Decidir qué hacer sin `db_filter` o con `"*"`: mantener el
      comportamiento anterior + advertencia explícita en pantalla.
- [x] Implementar el filtro `datname ~ '<patron>'`, con escape de comillas
      simples del patrón.
- [x] Confirmar que el fix cubre todos los call sites al vivir dentro de la
      función misma (`prompt_for_database`, handler de `update`).
- [x] Probar contra `integra-17.0` (17 bases → 1) y contra una instancia con
      `db_filter` amplio (`^comercial-19_` → 7 bases hermanas correctas).
