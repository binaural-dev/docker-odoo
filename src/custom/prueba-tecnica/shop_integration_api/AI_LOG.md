---

### `src/custom/shop_integration_api/AI_LOG.md`

```markdown
# AI_LOG — shop_integration_api

## Herramientas
- Gemini 3.8 Flash / AI studio

## Prompts clave
1. *Diseñar un controlador REST en Odoo 19 tipo HTTP con autenticación Bearer usando res.users.apikeys y respuestas JSON personalizadas sin envoltorio RPC.*
   - Se definió el endpoint `POST` usando `type='http'` y `request.make_json_response()`.
2. *Manejar validaciones de stock y parámetros GET sin que excepciones de tipo de fecha produzcan errores HTTP 500.*
   - Se estructuró el helper `_parse_datetime` y la respuesta HTTP 400 controlada.
3. *Implementar mecanismo de idempotencia en Odoo usando SHA-256 del cuerpo HTTP y cabecera Idempotency-Key.*
   - Se modeló la persistencia en `shop.idempotency.key` y la validación de colisiones (409).

## Lo que la IA hizo mal
1. **Campo `groups_id` obsoleto:** La IA intentó asignar permisos al usuario de pruebas usando `groups_id`, lo cual falló inmediatamente en Odoo 19 (`ValueError: Invalid field 'groups_id' in 'res.users'`). Se corrigió a `group_ids`.
2. **Transacciones de solo lectura en rutas `auth='none'`:** La IA omitió que en Odoo 19 las rutas públicas arrancan en modo réplica de lectura. Al intentar guardar el log o el pedido, PostgreSQL falló con `ERROR: cannot execute INSERT in a read-only transaction`. Se resolvió agregando `readonly=False` en el decorador `@http.route`.
3. **Manejo de `res.users.apikeys`:** La IA sugirió `scope=None` y `expiration_date=None`, disparando `AssertionError: scope and key required` y claves auto-expiradas. Se corrigió pasando `scope='rpc'`, ejecutando `.with_user(user)` y asignando una fecha futura de expiración.

## Lo que escribiste tú sin IA
- Configuración de listas de control de acceso (`security/ir.model.access.csv`) para los grupos de venta y almacén en los tests.
- Diseño de las vistas de lista `<list>` en solo lectura bajo **Ajustes › Técnico**.
