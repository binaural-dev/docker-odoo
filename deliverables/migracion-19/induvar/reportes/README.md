# Comparación de reportes legales 17 vs 19 (Induvar)

Ejecuta los reportes legales de nómina con los mismos parámetros en Odoo 17 y en Odoo 19
y compara lo que entregan (el `data` de `report_action` o el contenido del TXT).

- `dump_reports.py`: INCES, MPPPST (PDF + 2 TXT), FAOV, horas extra y ARC por compañía y período.
- `dump_faov.py`: FAOV con los tipos de estructura cargados (sin ellos el asistente no trae recibos).
- `run17.py`: carga Odoo 17 con los addons de Induvar sin `odoo shell`. En `odoo-thk` el espacio
  de nombres `odoo.addons` traía las rutas de thk aunque el addons path dijera idv.
- `compare.py 17.json 19.json`: diferencias por reporte, con tolerancia de 0,01.

Cómo se corrió (2026-09-29):
- 19: `docker exec -e OUT=/tmp/x.json odoo-idv_19 bash -lc "odoo shell -c /home/odoo/.config/odoo.conf -d 19_idv --no-http < /tmp/dump_reports.py"`
- 17: `docker exec -e OUT=/tmp/x.json odoo-thk python3 /tmp/run17.py` (con `/tmp/idv17.conf` = `[options]` vacío)

Resultados: `reportes_17.json`, `reportes_19.json` (con los arreglos #2910 + #2920) y
`reportes_19_sin_arreglos.json` (la primera corrida, que mostró el bug de las reglas archivadas).
