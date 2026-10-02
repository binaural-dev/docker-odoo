---
name: mig-exportar-configuracion
description: Exporta la configuracion viva (no transaccional) de una instancia Odoo en la nube -- compania, plan de cuentas, impuestos, posiciones fiscales, almacenes, listas de precio, POS, usuarios, automatizaciones -- a archivos Excel organizados por dominio, listos para importar a mano con el importador nativo de Odoo en otro ambiente (tipicamente el destino de una migracion de version). Usar cuando el usuario pida copiar/migrar la configuracion de un cliente hacia otro ambiente, o prepare el "seed" de datos de un ambiente nuevo a partir de produccion. No migra codigo de modulos (ver mig-version-upgrade) ni importa nada directo a destino: deja los Excel + un README con el orden de importacion para que una persona los cargue.
---

# mig-exportar-configuracion

Extrae configuracion (no datos transaccionales: nada de facturas, pedidos,
movimientos de stock) de una instancia Odoo de origen, via el conector de
solo lectura `core:odoo-cloud`, y la deja en archivos `.xlsx` listos para el
importador nativo de Odoo (*Ajustes > Tecnico > Importar*) en el ambiente
destino. Nace de un caso real de migracion de version (v16 produccion ->
v19), donde la migracion de **codigo** se resolvio por separado y dejo la de
datos explicitamente fuera de alcance.

**Version 1 -- piloto.** Igual que `mig-version-upgrade`, nace para un caso
real concreto. Si una corrida real encuentra un dominio/modelo que falta o un
campo mal resuelto, la correccion va a `tools/domains.json` (declarativo)
antes que al script.

Reutiliza, sin duplicar su logica: el cliente JSON-RPC de solo lectura de
`core:odoo-cloud` (`odoo_client.py` -- mismo mecanismo de autenticacion,
misma whitelist de metodos, **nunca escribe**), y la misma idea de
"preguntar alcance, nunca asumir" que ya usa `mig-version-upgrade`.

## Informacion necesaria

1. **Instancia origen** -- *preguntar siempre*. Debe existir ya en
   `~/.config/odoo-cloud/config.json` (si no, remitir a `core:odoo-cloud`
   para configurarla antes de seguir).
2. **Instancia/ambiente destino** -- *preguntar siempre*, aunque este export
   no escriba ahi: se usa para decidir que dominios tienen sentido ya (ver
   Paso 0.2) y para el README final.
3. **Dominios en alcance de esta corrida** -- *preguntar siempre* con
   `AskUserQuestion`, nunca asumir "todos". Ver tabla de dominios en
   `tools/domains.json`.

## Paso 0 -- Alcance y estado del destino

1. Confirmar que la instancia origen responde: `python3 ~/.claude/agents/mig-exportar-configuracion/tools/export_config.py`
   usa el mismo config que `odoo_client.py whoami -i <origen>` -- si falla,
   resolverlo ahi primero (no es responsabilidad de esta skill).
2. **Antes de ofrecer el dominio `pos`** (o cualquier dominio marcado con
   `requiere_modulos_instalados` en `domains.json`), verificar el estado real
   del destino:
   ```bash
   python3 <ruta-odoo-cloud>/odoo_client.py -i <destino> search_read ir.module.module \
     --domain '[["name","in",["point_of_sale", "<modulos custom relevantes>"]]]' \
     --fields name,state
   ```
   Si figuran `uninstalled`, avisar explicitamente que ese dominio se puede
   generar igual (el export no depende del destino) pero **no importar
   todavia** -- dejarlo anotado en el README en vez de omitirlo en silencio.
3. Preguntar con `AskUserQuestion` que dominios de `tools/domains.json`
   entran en esta corrida (default sugerido: todos los que no dependan de
   modulos no instalados en destino, pero confirmar).

## Paso 1 -- Extraccion

```bash
python3 ~/.claude/agents/mig-exportar-configuracion/tools/export_config.py --source <origen> --domain <dom1,dom2|all> [--custom-path src/custom/<cliente>]
```

Por cada modelo del dominio: `fields_get` (campos reales del origen,
excluyendo binarios/one2many/no-almacenados) -> `search_read` completo ->
un `.xlsx` por modelo, con un External ID sintetico
(`__export__.<modelo>_<id>`) para que los campos relacionales referencien
registros de **otros modelos exportados en la misma corrida** sin depender
de que los IDs numericos coincidan en destino. Una referencia a un modelo
fuera de alcance queda marcada `# REVISAR: <nombre legible>` en la celda --
no se pierde el dato, pero requiere completar el external id a mano o
re-correr incluyendo el dominio que trae ese modelo.

## Paso 2 -- Compatibilidad de version (advierte, no bloquea)

El script ya genera `notas-version.md` por dominio comparando cada campo
exportado contra el core de Odoo 19 clonado localmente (por defecto
`~/binaural/Core Odoo/odoo-19.0` y `src/enterprise-19.0` de docker-odoo;
sobreescribible con `ODOO_CORE_PATHS`, y el custom del cliente con
`--custom-path`). Es una heuristica
(busca `<campo> = fields.` en el checkout) -- cero coincidencias es señal
real de campo eliminado/renombrado (ya paso con `ir.cron.numbercall` en una
migracion de codigo previa), pero no reemplaza una revision
humana antes de importar. Leer ese archivo con el usuario antes de dar el
export por bueno.

## Paso 3 -- Entrega

El `README.md` generado en la raiz del export (ver `tools/export_config.py`,
`write_readme`) ya trae el orden de importacion recomendado y las
advertencias de referencias fuera de alcance. **No importar nada
automaticamente**: mismo principio que el conector `odoo-cloud` (solo
lectura) y el flujo de escritura humano de Binaural -- la importacion real la
hace una persona desde el ambiente destino.

## Donde queda todo

- Salida (datos reales del cliente, **confidencial, fuera de cualquier repo**):
  `~/binaural/config-export/<origen>/<fecha>/<dominio>/*.xlsx` +
  `notas-version.md` + `README.md` en la raiz del export. Esta carpeta vive
  fuera de `docker-odoo` a proposito -- nunca cerca de un `.git`, para que no
  haya riesgo de commitear datos reales de produccion de un cliente.
- Config declarativo de dominios: `tools/domains.json` (editar aqui para
  agregar/quitar modelos o campos, no en `export_config.py`).
