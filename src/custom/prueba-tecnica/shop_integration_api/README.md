# API para la tienda en línea (`shop_integration_api`)

Endpoints para que la tienda en línea consulte productos con su stock y cree pedidos de venta en Odoo 18.
Esta página es la documentación para el equipo de la tienda.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — `GET /api/v1/products` con filtros | ✅ |
| B — API keys (Bearer), `POST /api/v1/orders`, errores con el campo exacto, log de llamadas | ✅ 34 pruebas `HttpCase` en total, cobertura 93 %, sin advertencias |
| C — paginación, Idempotency-Key, stock sin una consulta por producto, webhook, `openapi.yaml` | ⏳ Pendiente |

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

Productos **activos** que **se pueden vender**, ordenados por código.

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "https://<servidor>/api/v1/products?category_id=5&in_stock=true&updated_since=2026-10-01T00:00:00Z"
```

| Parámetro | Tipo | Ejemplo | Qué hace |
|---|---|---|---|
| `category_id` | entero | `5` | Solo productos de esa categoría **y de sus subcategorías** |
| `in_stock` | `true` / `false` (también `1` / `0`) | `true` | `true`: solo productos con cantidad disponible mayor que cero |
| `updated_since` | fecha o fecha y hora ISO 8601 | `2026-10-27`, `2026-10-27T14:30:00Z`, `2026-10-27T10:30:00-04:00` | Solo productos modificados desde ese momento. **Sin zona se toma como UTC** |

Los filtros son opcionales y combinables. En la URL, un `+` de zona horaria se envía como `%2B`.

**Respuesta `200`:**

```json
{
  "currency": "USD",
  "count": 1,
  "data": [
    {"id": 1, "default_code": "DEMO-1", "name": "Mouse", "price": 25.0, "available_qty": 4.0}
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
| 400 | `INVALID_PARAMETER` | `category_id` / `in_stock` | Valor que no es un número o no es `true`/`false` |
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

## Cómo probarlo

```bash
./odoo test prueba-tecnica shop_integration_api -d api_prueba
```

Todas las pruebas son `HttpCase`: llaman por HTTP con la API key de un usuario de integración real.

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

## Supuestos

- **El pedido queda confirmado** (no como cotización): la tienda ya cerró la venta con el cliente, así que
  Odoo genera la entrega de inmediato. Es la base para el aviso al validar la entrega (tramo C).
- **El cliente debe existir** en Odoo: la API no crea clientes, para no duplicar fichas ni saltarse la
  revisión de crédito y datos fiscales. Pregunta para el cliente: ¿quieren que se cree automáticamente?
- **Precios**: los de la lista de precios del cliente en Odoo. La tienda no envía precios, para que no se
  puedan alterar desde afuera.
- `external_ref` es única por compañía. Un reintento con la misma referencia da `409` y no duplica el pedido.
  El tramo C agrega `Idempotency-Key` para que un reintento devuelva el mismo pedido.
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
  (`shop_external_ref`, compañía) resuelve el caso en que dos peticiones llegan al mismo tiempo.

## Limitaciones conocidas

- Un cambio de stock no cuenta como modificación para `updated_since`, porque los movimientos de inventario
  no cambian la fecha del producto. La tienda debe consultar el stock periódicamente (tramo C: paginación y
  aviso al validar entregas).
- Sin paginación (tramo C).
- No se probó en las pruebas el camino de error 500 ni el de dos peticiones simultáneas con la misma
  referencia (cubierto por la restricción única de la base).
