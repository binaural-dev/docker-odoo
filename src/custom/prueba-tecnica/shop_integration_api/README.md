# API para la tienda en línea (`shop_integration_api`)

Endpoints para que la tienda en línea consulte productos con su stock y, desde el tramo B, cree pedidos de
venta en Odoo 18. Esta página es la documentación para el equipo de la tienda.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — `GET /api/v1/products` con sesión de usuario y filtros | ✅ 14 pruebas `HttpCase`, cobertura 100 %, sin advertencias al instalar |
| B — API keys (Bearer), `POST /api/v1/orders`, log de llamadas | ⏳ Pendiente |
| C — paginación, Idempotency-Key, stock sin una consulta por producto, webhook, `openapi.yaml` | ⏳ Pendiente |

## Guía para la tienda

### 1. Usuario de la integración

Hay que pedirle a Odoo un **usuario dedicado** para la tienda, no el de una persona. La API trabaja con los
permisos de ese usuario (sin saltarse la seguridad de Odoo), así que necesita:

- *Ventas*: **Usuario: solo sus documentos**
- *Inventario*: **Usuario**

Sin el permiso de inventario, la API responde `403 FORBIDDEN` (ver «Errores»).

### 2. Autenticación (tramo A: sesión)

En el tramo A la autenticación es la **sesión de usuario** de Odoo (`auth='user'`). Primero se inicia sesión y
luego se envía la cookie `session_id` en cada llamada:

```bash
# Iniciar sesión (guarda la cookie en cookies.txt)
curl -c cookies.txt -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"db":"<base>","login":"<usuario>","password":"<contraseña>"}}' \
  https://<servidor>/web/session/authenticate

# Consultar productos con esa sesión
curl -b cookies.txt "https://<servidor>/api/v1/products?in_stock=true"
```

Sin sesión, Odoo redirige al formulario de login (`303` → `/web/login`). Si en el servidor hay varias bases
de datos y no hay `dbfilter`, responde `404`, porque no sabe a qué base va la llamada. En el tramo B esto se
reemplaza por API keys en la cabecera `Authorization: Bearer`.

### 3. `GET /api/v1/products`

Devuelve los productos **activos** que **se pueden vender** (*Puede ser vendido*), ordenados por código.

| Parámetro | Tipo | Ejemplo | Qué hace |
|---|---|---|---|
| `category_id` | entero | `5` | Solo productos de esa categoría **y de sus subcategorías** |
| `in_stock` | `true` / `false` (también `1` / `0`) | `true` | `true`: solo productos con cantidad disponible mayor que cero |
| `updated_since` | fecha o fecha y hora ISO 8601 | `2026-10-27`, `2026-10-27T14:30:00Z`, `2026-10-27T10:30:00-04:00` | Solo productos modificados desde ese momento. **Sin zona se toma como UTC** |

Los filtros son opcionales y se pueden combinar. Si en la zona horaria se usa `+`, hay que enviarlo como
`%2B` en la URL (por ejemplo, `...T10:30:00%2B01:00`), porque en una URL el `+` se lee como espacio.

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
| `default_code` | Referencia interna (código). `null` si el producto no tiene |
| `name` | Nombre, con los valores de la variante si los tiene (p. ej. «Camisa (Rojo, M)») |
| `price` | Precio de venta de la ficha del producto, **sin impuestos**, en la moneda de `currency` |
| `available_qty` | Cantidad **disponible para vender**: lo que hay en los almacenes de la compañía menos lo ya reservado para otros pedidos |

### 4. Errores

Todos los errores usan el mismo formato y un código HTTP acorde:

```json
{"error": {"code": "INVALID_DATE", "field": "updated_since", "message": "La fecha «27/10/2026» no es válida. Use AAAA-MM-DD o AAAA-MM-DDTHH:MM:SS (UTC), por ejemplo 2026-10-27T14:30:00."}}
```

| HTTP | `code` | `field` | Cuándo |
|---|---|---|---|
| 400 | `INVALID_DATE` | `updated_since` | Fecha mal escrita o imposible (`27/10/2026`, `2026-13-01`, `ayer`) |
| 400 | `INVALID_PARAMETER` | `category_id` / `in_stock` | Valor que no es un número o no es `true`/`false` |
| 422 | `CATEGORY_NOT_FOUND` | `category_id` | La categoría no existe |
| 403 | `FORBIDDEN` | `null` | El usuario de la integración no tiene permiso para ver productos o inventario |
| 405 | — | — | Método distinto de `GET` |

Ninguna entrada mal escrita produce un error 500.

## Cómo probarlo

```bash
./odoo test prueba-tecnica shop_integration_api -d api_prueba
```

Las pruebas (`HttpCase`) llaman al endpoint por HTTP con un usuario de integración real, no como
administrador:

| Qué se prueba | Prueba |
|---|---|
| Campos y valores de la respuesta, `Content-Type` JSON | `test_response_fields`, `test_response_is_json` |
| Solo activos y vendibles | `test_only_active_and_sellable` |
| Cada filtro solo: categoría (con subcategorías), con stock, modificados desde (con y sin zona horaria) | `test_filter_category_includes_children`, `test_filter_in_stock`, `test_filter_updated_since` |
| Un cambio de precio en la plantilla cuenta como modificación | `test_updated_since_sees_template_changes` |
| Filtros combinados | `test_filters_combined` |
| Fechas, categorías y booleanos inválidos → 400/422 con el campo exacto | `test_invalid_date`, `test_invalid_category`, `test_invalid_in_stock` |
| Sin sesión → login; sin permisos de inventario → 403; solo `GET` | `test_requires_login`, `test_user_without_stock_rights`, `test_only_get` |

Además se probó en vivo con `curl` sobre la instancia local: login con `/web/session/authenticate`, consulta
con filtros, fecha mala (400) y llamada sin sesión.

## Supuestos

- **«Cantidad disponible» = `free_qty`** (a mano menos reservado), no la cantidad a mano. Para una tienda, lo
  que importa es lo que se puede vender sin quitárselo a otro pedido.
- El stock es el de **todos los almacenes de la compañía** del usuario de la integración.
- **Precio = precio de venta de la ficha**, sin impuestos y sin listas de precios. Si la tienda necesita
  precios por lista o con impuestos, se agrega un parámetro.
- «Modificados desde» compara la fecha de modificación de la **variante o de la plantilla**, porque precio y
  nombre están en la plantilla.
- Se devuelven variantes (`product.product`), porque cada variante tiene su propio código y su propio stock.

## Limitaciones conocidas

- **Un cambio de stock no cuenta como modificación:** los movimientos de inventario no cambian la fecha de
  modificación del producto. Para mantener el stock al día, la tienda debe consultar sin `updated_since`, o
  con `in_stock`, cada cierto tiempo. El tramo C agrega paginación y un aviso (webhook) al validar entregas.
- Sin paginación en el tramo A: devuelve todos los productos que cumplen los filtros (tramo C).
- La autenticación por sesión es la que pide el tramo A. Para un sistema externo lo correcto son API keys
  (tramo B).
