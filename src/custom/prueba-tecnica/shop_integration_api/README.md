# API para la tienda en línea (`shop_integration_api`)

Endpoints para que la tienda en línea consulte productos con su stock y cree pedidos de venta en Odoo 18.
Esta página es la documentación para el equipo de la tienda.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — `GET /api/v1/products` con filtros | ✅ |
| B — API keys (Bearer), `POST /api/v1/orders`, errores con el campo exacto, log de llamadas | ✅ |
| C — paginación, Idempotency-Key, stock sin una consulta por producto (con prueba), webhook con reintentos, [`openapi.yaml`](openapi.yaml) | ✅ 57 pruebas en total, cobertura 94 %, sin advertencias |

La especificación completa (endpoints, esquemas, errores y webhook) está en [`openapi.yaml`](openapi.yaml)
(OpenAPI 3.1). Se puede abrir en Swagger Editor o importar en Postman.

## Guía para la tienda

### 1. Usuario y API key

1. La empresa crea en Odoo un **usuario dedicado** para la tienda (no el de una persona) con:
   - *Ventas*: **Usuario: solo sus documentos**
   - *Inventario*: **Usuario**
2. Con ese usuario: *Mi perfil › Seguridad de la cuenta › Nueva API key*. Odoo muestra la clave **una sola
   vez**: guárdela en el gestor de secretos de la tienda, nunca en el código.
3. Cada llamada lleva la cabecera:

   ```
   Authorization: Bearer <API key>
   ```

La API trabaja con los permisos de ese usuario: no se salta la seguridad de Odoo. Los pedidos quedan a su
nombre como vendedor. Para revocar el acceso basta con borrar la clave o archivar el usuario.

Si en el servidor hay varias bases de datos, debe existir un `dbfilter` que lleve el dominio de la API a la
base correcta. Si no, Odoo responde `404`.

### 2. `GET /api/v1/products`

Productos **activos** que **se pueden vender**, ordenados por código, **paginados**.

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "https://<servidor>/api/v1/products?category_id=5&in_stock=true&updated_since=2026-10-01T00:00:00Z"
```

| Parámetro | Tipo | Ejemplo | Qué hace |
|---|---|---|---|
| `category_id` | entero | `5` | Solo productos de esa categoría **y de sus subcategorías** |
| `in_stock` | `true` / `false` (también `1` / `0`) | `true` | `true`: solo productos con cantidad disponible mayor que cero |
| `updated_since` | fecha o fecha y hora ISO 8601 | `2026-10-27`, `2026-10-27T14:30:00Z`, `2026-10-27T10:30:00-04:00` | Solo productos modificados desde ese momento. **Sin zona se toma como UTC** |
| `page` | entero ≥ 1 (por defecto 1) | `2` | Página |
| `page_size` | entero de 1 a 200 (por defecto 50) | `100` | Productos por página |

Los filtros son opcionales y combinables. En la URL, un `+` de zona horaria se envía como `%2B`.

**Respuesta `200`:**

```json
{
  "currency": "USD",
  "count": 2,
  "total": 5,
  "page": 1,
  "page_size": 2,
  "next": "/api/v1/products?category_id=5&page_size=2&page=2",
  "data": [
    {"id": 11, "default_code": "PAG-1", "name": "Mouse", "price": 25.0, "available_qty": 4.0},
    {"id": 12, "default_code": "PAG-2", "name": "Camisa (Rojo, M)", "price": 18.5, "available_qty": 0.0}
  ]
}
```

| Campo | Qué es |
|---|---|
| `id` | Id del producto (variante) en Odoo |
| `default_code` | Referencia interna (código). `null` si no tiene. Es el código que se usa en los pedidos |
| `name` | Nombre, con los valores de la variante si los tiene (p. ej. «Camisa (Rojo, M)») |
| `price` | Precio de venta de la ficha, **sin impuestos**, en la moneda de `currency` |
| `available_qty` | Cantidad **disponible para vender**: lo que hay en los almacenes de la compañía menos lo ya reservado |
| `count` / `total` | Productos en esta página / que cumplen los filtros en todas las páginas |
| `next` | Ruta de la página siguiente, con los mismos filtros; `null` en la última. Para recorrer todo, siga `next` hasta que sea `null` |

El número de consultas a la base **no crece** con la cantidad de productos: nombre, precio y stock se calculan
para toda la página junta. Medido: 17 consultas tanto con 5 como con 60 productos (`test_query_count_does_not_grow`).

### 3. `POST /api/v1/orders`

Crea un pedido de venta **confirmado**.

```bash
curl -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"customer_vat": "J-12345678-9", "external_ref": "WEB-1001",
       "lines": [{"default_code": "SHOP-001", "quantity": 2}, {"default_code": "SHOP-003", "quantity": 1}]}' \
  https://<servidor>/api/v1/orders
```

| Campo | Obligatorio | Qué es |
|---|---|---|
| `customer_vat` | sí | RIF del cliente, que ya debe existir en Odoo. Se comparan solo letras y números, así que `J-12345678-9`, `J123456789` y `j 12345678 9` son el mismo RIF. Si el RIF es de un contacto de una empresa, el pedido va a nombre de la empresa |
| `external_ref` | sí | Número del pedido en la tienda. **Único**: no se pueden crear dos pedidos con la misma referencia |
| `lines` | sí, al menos una | Lista de `{"default_code": "<código>", "quantity": <número mayor que 0>}` |

**Respuesta `201`:**

```json
{
  "id": 42, "name": "S00042", "external_ref": "WEB-1001", "state": "sale",
  "customer": {"id": 7, "name": "Comercial Los Andes C.A.", "vat": "J-12345678-9"},
  "amount_untaxed": 130.0, "amount_tax": 0.0, "amount_total": 130.0, "currency": "USD",
  "lines": [
    {"default_code": "SHOP-001", "quantity": 2.0, "price_unit": 25.0, "subtotal": 50.0},
    {"default_code": "SHOP-003", "quantity": 1.0, "price_unit": 80.0, "subtotal": 80.0}
  ]
}
```

Si la llamada falla por cualquier motivo, **no se crea nada** (ni el pedido ni parte de él).

**Reintentos seguros con `Idempotency-Key`.** Envíe una clave propia por pedido (por ejemplo un UUID) en la
cabecera `Idempotency-Key`:

| Situación | Respuesta |
|---|---|
| Primera vez | `201` con el pedido |
| Misma clave y **mismo contenido** (un reintento por falla de red) | `200` con **el mismo pedido** y `Idempotent-Replayed: true`. No se crea otro |
| Misma clave y **otro contenido** | `409 IDEMPOTENCY_KEY_REUSED` |
| La primera llamada falló (por ejemplo, un código mal escrito) | La clave no queda usada: puede reintentar con los datos corregidos |
| Dos llamadas con la misma clave al mismo tiempo | Una crea el pedido; la otra recibe `409 IDEMPOTENCY_KEY_IN_USE` y, al reintentar, el mismo pedido |

«Mismo contenido» se compara con una huella SHA-256 del JSON normalizado: el orden de las claves no importa.
Las claves son por usuario de la integración. Sin la cabecera, repetir la misma `external_ref` da `409
DUPLICATE_EXTERNAL_REF`.

### 4. Errores

Todos los errores usan el mismo formato. `field` dice exactamente qué dato corregir; las líneas se
numeran **desde 0**, como en JSON:

```json
HTTP 422
{"error": {"code": "PRODUCT_NOT_FOUND", "field": "lines[1].default_code", "message": "No existe un producto con el código ABC-123"}}
```

| HTTP | `code` | `field` | Cuándo |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | `null` | Falta la cabecera `Authorization: Bearer …` (o tiene otro esquema). Una sesión de navegador no sirve |
| 401 | `INVALID_API_KEY` | `null` | Clave inexistente, revocada o vencida, o usuario archivado |
| 403 | `FORBIDDEN` | `null` | El usuario de la integración no tiene permisos suficientes (por ejemplo, de inventario) |
| 400 | `INVALID_DATE` | `updated_since` | Fecha mal escrita o imposible (`27/10/2026`, `2026-13-01`, `ayer`) |
| 400 | `INVALID_PARAMETER` | `category_id` / `in_stock` / `page` / `page_size` | Valor que no es un número, no es `true`/`false` o está fuera de rango |
| 400 | `INVALID_IDEMPOTENCY_KEY` | `Idempotency-Key` | La cabecera está vacía o tiene más de 255 caracteres |
| 422 | `CATEGORY_NOT_FOUND` | `category_id` | La categoría no existe |
| 400 | `INVALID_JSON` | `null` | El cuerpo no es JSON o no es un objeto |
| 422 | `MISSING_FIELD` | `customer_vat`, `external_ref`, `lines`, `lines[i].default_code` | Falta el dato o está vacío |
| 422 | `CUSTOMER_NOT_FOUND` | `customer_vat` | No hay un cliente con ese RIF |
| 422 | `AMBIGUOUS_CUSTOMER` | `customer_vat` | Hay más de una empresa con ese RIF; la empresa debe depurarlo |
| 422 | `INVALID_LINE` | `lines[i]` | La línea no es un objeto |
| 422 | `PRODUCT_NOT_FOUND` | `lines[i].default_code` | No hay un producto vendible y activo con ese código |
| 422 | `AMBIGUOUS_PRODUCT` | `lines[i].default_code` | Hay más de un producto con ese código |
| 422 | `INVALID_QUANTITY` | `lines[i].quantity` | La cantidad no es un número (por ejemplo `"2"`) o es cero o negativa |
| 422 | `BUSINESS_RULE` | `null` | Odoo rechazó el pedido por una regla de negocio; el mensaje dice cuál |
| 409 | `DUPLICATE_EXTERNAL_REF` | `external_ref` | Ya existe un pedido con esa referencia (también si llegan dos a la vez) |
| 409 | `IDEMPOTENCY_KEY_REUSED` | `Idempotency-Key` | La clave ya se usó con otro contenido |
| 409 | `IDEMPOTENCY_KEY_IN_USE` | `Idempotency-Key` | Otra petición con la misma clave se procesó al mismo tiempo; reintente |
| 405 | — | — | Método HTTP distinto del indicado |
| 500 | `INTERNAL_ERROR` | `null` | Error inesperado de Odoo. Queda en el log; avise a la empresa |

Ninguna entrada mal escrita produce un error 500.

### 5. Registro de llamadas (para la empresa)

*Ventas › Configuración › Llamadas de la tienda en línea* (administradores y gerentes de ventas). Cada
llamada, **también las que fallan**, queda con fecha, método, endpoint, usuario (vacío si no se pudo
autenticar), código HTTP, código de error, duración en ms, IP, referencia externa y pedido creado. Se puede
filtrar por «Con error» y agrupar por endpoint, código o día.

**El log nunca guarda la API key** (ni completa ni una parte). Hay una prueba que revisa todas las columnas
de cada fila.

### 6. Aviso a la tienda cuando se entrega el pedido (webhook)

Cuando en Odoo se **valida una entrega** de un pedido creado por la API, Odoo envía un `POST` a la URL de la
tienda con el evento `order.delivered`. El contenido, las cabeceras y la firma están en
[`openapi.yaml`](openapi.yaml) (sección `webhooks`).

**Configuración (empresa):** *Ajustes › Técnico › Parámetros del sistema*:
- `shop_integration_api.webhook_url`: URL de la tienda. Sin ella no se generan avisos.
- `shop_integration_api.webhook_secret`: secreto compartido para la firma.

**Para la tienda:**
- Responda `2xx` para confirmar. Cualquier otro código, un error de conexión o más de **10 s** de espera
  cuentan como fallo, y Odoo reintenta a los **1, 5, 15, 30, 60, 120 y 240 minutos** (8 intentos, unas 8 horas).
- Verifique `X-Shop-Signature: sha256=<HMAC-SHA256 del cuerpo con el secreto>`.
- Un aviso puede llegar **más de una vez**: ignore un `X-Shop-Event-Id` que ya procesó.
- Una entrega parcial genera un aviso por cada entrega validada (`is_partial`, `is_backorder`).

**Quien valida la entrega nunca espera ni ve un error de la tienda.** Validar solo **encola** el aviso, sin
ninguna llamada HTTP. El envío lo hace una acción planificada (*Tienda en línea: enviar avisos*), que se
dispara al encolar y además cada 5 minutos. Si encolar fallara por un error inesperado, la entrega se valida
igual y el error queda en el registro.

*Ventas › Configuración › Avisos a la tienda en línea*: estado de cada aviso (pendiente, enviado o fallido),
intentos, próximo intento y último error, con el botón **Reintentar ahora**.

## Cómo probarlo

```bash
./odoo test prueba-tecnica shop_integration_api -d api_prueba
```

Las pruebas de la API son `HttpCase`: llaman por HTTP con la API key de un usuario de integración real.

| Qué se prueba | Prueba |
|---|---|
| **GET** · campos, solo activos y vendibles, cada filtro solo y combinados, zona horaria, cambios en la plantilla, errores de parámetros, 403 sin inventario, solo `GET` | `TestProductsApi` (13 pruebas) |
| **401** sin cabecera, con clave inválida o modificada, con otro esquema (`Basic`), con solo sesión de navegador, y con usuario archivado | `TestApiAuthentication` |
| La llamada se hace como el usuario dueño de la clave | `test_key_acts_as_its_user` |
| **POST** · pedido confirmado con cliente, líneas, total, vendedor y entrega | `test_create_order` |
| RIF con distintos formatos | `test_vat_is_normalized` |
| RIF inexistente, producto inexistente (`lines[1].default_code`), producto no vendible | `test_customer_not_found`, `test_product_not_found_points_to_line`, `test_not_sellable_product_is_not_found` |
| Cantidad `0`, negativa, `"2"`, `null`, `true` → `lines[1].quantity` | `test_invalid_quantities` |
| Campos faltantes, JSON inválido | `test_missing_fields`, `test_invalid_json` |
| Si falla, no se crea nada | `test_failed_call_creates_nothing` |
| Referencia repetida → 409 y un solo pedido | `test_duplicate_external_ref_is_409` |
| **Log** · cada llamada (200, 400, 401, 201) con usuario, código, duración, referencia y pedido | `test_every_call_is_logged` |
| El log no guarda la clave | `test_log_never_stores_the_key` |
| El usuario de la integración no lee el log | `test_integration_user_cannot_read_logs` |
| Cada petición se ejecuta una sola vez (sin reintentos de Odoo por cursor de solo lectura) | `test_each_call_runs_once` |
| **C · Paginación** · total, página y `next` con los filtros, sin repetidos ni faltantes; seguir `next`; página vacía al final; valores por defecto; parámetros inválidos | `TestPagination` (5 pruebas) |
| **C · Consultas** · las mismas con 5 que con 60 productos (17), con todos los filtros | `test_query_count_does_not_grow` |
| **C · Idempotency-Key** · mismo contenido → mismo pedido (`200`, `Idempotent-Replayed`); orden de claves indiferente; otro contenido → `409`; una llamada fallida no consume la clave; claves por usuario; sin clave → duplicado; clave inválida | `TestIdempotency` (8 pruebas) |
| **C · Webhook** · validar solo encola (no llama a la tienda); contenido del aviso; envío firmado (HMAC) con `X-Shop-Event-Id` y tiempo de espera | `test_validation_only_enqueues`, `test_cron_sends_signed_event` |
| **C · Tienda caída** · la entrega se valida igual; el aviso queda pendiente con el error y no se reintenta antes de tiempo | `test_store_down_does_not_affect_validation_and_retries` |
| **C · Reintentos** · esperas de 1, 5, 15, 30, 60, 120 y 240 min y luego «fallido»; recuperación cuando la tienda vuelve | `test_retries_with_growing_delays_then_fails`, `test_recovers_after_store_comes_back` |
| **C** · Solo pedidos de la tienda; sin URL no hay avisos; si encolar falla, la entrega se valida igual; botón «Reintentar ahora» | `test_only_shop_orders_and_only_deliveries`, `test_no_url_no_events`, `test_enqueue_failure_does_not_break_validation`, `test_retry_now_button` |

## Supuestos

- **El pedido queda confirmado** (no como cotización): la tienda ya cerró la venta con el cliente, así que
  Odoo genera la entrega de inmediato. Es la base para el aviso al validar la entrega (tramo C).
- **El cliente debe existir** en Odoo: la API no crea clientes, para no duplicar fichas ni saltarse la
  revisión de crédito y datos fiscales. Pregunta para el cliente: ¿quieren que se cree automáticamente?
- **Precios**: los de la lista de precios del cliente en Odoo. La tienda no envía precios, para que no se
  puedan alterar desde afuera.
- `external_ref` es única por compañía. Un reintento sin `Idempotency-Key` da `409` y no duplica el pedido;
  con la clave, devuelve el mismo pedido.
- Un reintento con `Idempotency-Key` responde `200` (no `201`) para que la tienda sepa que no se creó nada nuevo.
- El aviso se envía **al menos una vez** (puede repetirse): por eso lleva `X-Shop-Event-Id`. Garantizar «exactamente
  una vez» requiere que la tienda deduplique.
- **«Cantidad disponible» = `free_qty`** (a mano menos reservado), en todos los almacenes de la compañía.
- Las líneas de `lines` se numeran desde 0, como los arreglos en JSON.
- **Comisiones:** si está instalado `sale_commission`, el vendedor de los pedidos web es el usuario de la
  integración, así que la comisión se calcula con su porcentaje. Pregunta para el cliente: ¿quién cobra
  comisión por las ventas web?

## Decisiones de diseño

- **API keys nativas** (`res.users.apikeys`, alcance `rpc`, el mismo que usa XML-RPC/JSON-RPC). No se usa
  `auth='bearer'` de Odoo, porque responde con su propio formato y acepta también la sesión del navegador.
  Aquí la clave se valida con `_check_credentials` y luego la petición corre **como el usuario dueño de la
  clave** (`request.update_env`). Sin `sudo()` para productos ni pedidos.
- **Un único punto de entrada** (`_handle`) para autenticar, ejecutar dentro de un *savepoint* y registrar la
  llamada. Si algo falla, el savepoint deshace lo que se alcanzó a escribir y el log igual se guarda.
- **`sudo()` solo para escribir el log**: el usuario de la integración no tiene (ni debe tener) acceso al
  registro de llamadas.
- **Rutas `readonly=False`**: Odoo 18 abre los `GET` con un cursor de solo lectura. Como cada llamada escribe
  su log, Odoo reintentaría la petición completa con otro cursor, es decir, la ejecutaría dos veces. Se
  detectó en el registro de las pruebas y ahora hay una prueba que lo impide.
- **Duplicados simultáneos:** además de buscar la referencia antes de crear, una restricción única en la base
  (`shop_external_ref`, compañía) resuelve el caso en que dos peticiones llegan al mismo tiempo. Lo mismo para
  `Idempotency-Key` (`key`, usuario).
- **Idempotencia:** la clave se registra junto con el pedido, dentro de la misma transacción. Si la llamada
  falla, no queda registrada y se puede reintentar. `sudo()` solo para esa tabla técnica, siempre filtrada por
  el usuario autenticado.
- **Webhook con cola (transactional outbox):** la validación de la entrega solo crea un registro en
  `shop.webhook.event`, dentro de su transacción. Si la entrega se deshace, el aviso también. El envío HTTP
  ocurre después, en la acción planificada, con tiempo de espera de 10 s, `FOR UPDATE SKIP LOCKED` para no
  enviar dos veces a la vez y un `commit` por aviso. `sudo()` para encolar, porque quien valida (almacén) no
  tiene acceso a la cola.
- **Stock en lote:** `free_qty` es un campo calculado que Odoo resuelve para todo el conjunto de productos con
  una sola lectura de cantidades. Se lee sobre la página completa, nunca producto por producto. El filtro
  `in_stock` también va en el dominio (no se filtra en Python).

## Limitaciones conocidas

- Un cambio de stock no cuenta como modificación para `updated_since`, porque los movimientos de inventario
  no cambian la fecha del producto. La tienda debe recorrer el stock periódicamente (con la paginación); el
  aviso al validar entregas le informa lo que salió por sus propios pedidos.
- Las claves de idempotencia no vencen. Con mucho volumen convendría una acción planificada que borre las de
  más de, por ejemplo, 30 días.
- La URL y el secreto del webhook se configuran como parámetros del sistema (sin pantalla de ajustes propia).
- `openapi.yaml` se validó como YAML y se revisó a mano; no se pasó por un validador formal de OpenAPI.
- No se probó en las pruebas el camino de error 500 ni el de dos peticiones simultáneas con la misma
  referencia (cubierto por la restricción única de la base).
