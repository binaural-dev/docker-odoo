# AI Log - Ejercicio 1: API REST (`shop_integration_api`)

## Herramientas
- Antigravity (Google DeepMind / Gemini)

---

## Prompts clave
1. "¿Cómo estructurar en Odoo 17 un controlador HTTP tipo GET con respuesta JSON limpia utilizando `request.make_json_response` y manejando códigos de estado HTTP 422 para validaciones de parámetros?"
   - *Respuesta:* Proveyó la sintaxis moderna de Odoo 17 donde `request.make_json_response(dict, status=...)` reemplaza a la serialización manual con `werkzeug.wrappers.Response`.
2. "¿Cómo estructurar pruebas de integración HTTP en Odoo 17 utilizando `odoo.tests.HttpCase` que requieran sesión de usuario y validen status codes y respuestas JSON?"
   - *Respuesta:* Mostró el uso de `self.authenticate(user, pass)` seguido de `self.url_open(endpoint)` y `response.json()`.
3. "¿Cuál es el mejor manejo en Python/Odoo para parsear fechas ISO-8601 soportando tanto `YYYY-MM-DD` como `YYYY-MM-DDTHH:MM:SS` sin lanzar un error 500?"
   - *Respuesta:* Sugirió combinar `datetime.fromisoformat` y fallback con `fields.Datetime.to_datetime`, capturando excepciones para retornar el código 422 con formato estructurado.

---

## Lo que la IA hizo mal o se corrigió
- Inicialmente sugirió usar `type='json'` en la ruta `@http.route`.
  - *Cómo me di cuenta:* Las rutas `type='json'` en Odoo fuerzan el protocolo JSON-RPC 2.0 (exigiendo un payload con `"jsonrpc": "2.0"` y devolviendo siempre HTTP 200 con un campo `"result"` o `"error"`). Para una API REST estándar consumida por un e-commerce externo (GET con query params y status code HTTP 200/422/500 directo), se debe usar `type='http'` y responder con `request.make_json_response`.
- Propuso depender únicamente de `['base', 'product']` ignorando que el campo `qty_available` pertenece al módulo de inventario (`stock`).
  - *Cómo me di cuenta:* Si `stock` no está instalado o no se declara como dependencia, `product.product` no posee `qty_available` en Odoo estándar y la búsqueda de `only_stock` fallaría en base limpia. Se agregó `stock` a las dependencias y una guarda defensiva `hasattr(p, 'qty_available')`.

---

## Pruebas ejecutadas, fallos y soluciones
- Se ejecutó el script `scripts/odoo-test` con el contenedor `odoo-prueba-tecnica` para `shop_integration_api` midiendo cobertura con `coverage`.
- **Fallo 1 (`ValidationError: Quants cannot be created for consumables or services`):**
  - *Causa:* En Odoo, el tipo por defecto de un producto al crearlo es consumible (`type='consu'`). Al intentar registrar existencias con `stock.quant.create()` el modelo lanzó validación impidiendo crear cuantificadores para consumibles.
  - *Solución:* Se especificó explícitamente `type='product'` (almacenable) en la creación de los productos de prueba.
- **Fallo 2 (`AccessError: You are not allowed to access 'Stock Move' records`):**
  - *Causa:* El campo computado `qty_available` calcula movimientos de almacén (`stock.move`). El usuario de prueba carecía del grupo de inventario, provocando un error de permisos en el cómputo.
  - *Solución:* Se otorgó el grupo `stock.group_stock_user` al usuario `shop_api_user` en el test y se blindó el endpoint con `p.sudo().qty_available` para permitir lectura segura de cantidades al catálogo externo sin comprometer seguridad.
- **Fallo 3 (Aserción de código 200 en `test_unauthenticated_request_is_not_allowed`):**
  - *Causa:* `self.url_open` por defecto sigue las redirecciones HTTP (303 -> 200 `/web/login`).
  - *Solución:* Se configuró `allow_redirects=False` para verificar directamente el código 303 de redirección.
- **Resultado final:** 8 de 8 pruebas aprobadas (100% OK), 0 errores, 0 fallos, **92% de cobertura de código**.

---

## Mayor riesgo del cambio
- El mayor riesgo técnico en controladores HTTP de Odoo al usar `auth='user'` radica en el comportamiento ante peticiones sin autenticar o con sesiones expiradas: si no se configuran adecuadamente las excepciones o el cliente espera JSON, Odoo por defecto redirige a `/web/login` en HTML. En la documentación del `README.md` se especificó explícitamente el procedimiento para obtener la cookie de sesión mediante `/web/session/authenticate`.

---

## Lo que escribiste tú sin IA
- El diseño del formato uniforme de respuestas de error JSON (`code`, `field`, `message`).
- La configuración de datos maestros y cuantificadores de stock en `setUpClass` de la prueba `HttpCase`.

