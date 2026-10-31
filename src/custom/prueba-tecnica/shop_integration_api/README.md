# API de Integración con Tienda Externa (`shop_integration_api`)

Módulo que expone endpoints REST en Odoo 17 para sincronización de catálogo de productos con plataformas externas de e-commerce (Next.js, Shopify, WooCommerce, aplicaciones móviles).

---

## Tramos Completados

- **Tramo A:** Endpoint `GET /api/v1/products` con soporte para filtros por categoría (`category_id`), stock disponible (`only_stock`) y fecha de actualización (`updated_since`). Manejo estructurado de errores en formato JSON con código HTTP 422 para filtros inválidos (sin tracebacks ni errores 500 no controlados). Suite completa de pruebas con `HttpCase` que certifica autenticación, filtros y respuestas HTTP.

---

## Especificación del Endpoint para Desarrolladores Externos

### 1. `GET /api/v1/products`

Obtiene el listado de productos activos y habilitados para venta en el sistema.

#### Autenticación
- Requiere autenticación de usuario (`auth='user'`). En pruebas de integración o aplicaciones web se utiliza la cookie de sesión (`session_id`) generada por `/web/session/authenticate`.
- `csrf=False`.

#### Parámetros de Consulta (Query Params)

| Parámetro | Tipo | Obligatorio | Descripción | Ejemplo |
|---|---|:---:|---|---|
| `category_id` | Entero | No | Filtra productos pertenecientes a la categoría indicada (`categ_id`). | `?category_id=5` |
| `only_stock` | Booleano | No | Si es `true` o `1`, incluye exclusivamente productos con stock disponible mayor a cero (`qty_available > 0`). | `?only_stock=true` |
| `updated_since` | String (ISO-8601) | No | Devuelve productos modificados en o después de la fecha indicada (`write_date >= updated_since`). Formatos admitidos: `YYYY-MM-DD` o `YYYY-MM-DDTHH:MM:SS`. | `?updated_since=2026-01-15T00:00:00` |

#### Respuestas HTTP

##### 200 OK — Catálogo obtenido exitosamente
```json
[
  {
    "id": 14,
    "code": "LAP-01",
    "name": "Laptop Pro",
    "price": 1200.0,
    "qty_available": 10.0
  },
  {
    "id": 15,
    "code": "CAF-01",
    "name": "Cafetera Express",
    "price": 80.0,
    "qty_available": 0.0
  }
]
```

##### 422 Unprocessable Entity — Filtro con formato inválido
Si alguno de los parámetros provistos no puede ser procesado (por ejemplo, una fecha malformada o un ID no numérico), se retorna un error estructurado:

```json
{
  "error": {
    "code": "INVALID_FILTER",
    "field": "updated_since",
    "message": "Formato de fecha inválido. Use formato ISO-8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)."
  }
}
```

```json
{
  "error": {
    "code": "INVALID_FILTER",
    "field": "category_id",
    "message": "El parámetro category_id debe ser un número entero válido."
  }
}
```

##### 500 Internal Server Error — Error no controlado
Si ocurriese un error inesperado en base de datos o servidor, la respuesta devuelve un mensaje controlado sin exponer trazas de la aplicación:

```json
{
  "error": {
    "code": "SERVER_ERROR",
    "message": "Ocurrió un error inesperado al procesar la solicitud."
  }
}
```

---

## Cómo Probarlo

### 1. Ejecución de Tests Automatizados (`HttpCase`)
La suite ejecuta peticiones HTTP reales simulando un cliente web autenticado:

```bash
./odoo test prueba-tecnica shop_integration_api
```

O en la suite global sobre base de datos limpia:
```bash
./odoo test -d prueba_limpia -m shop_integration_api
```

### 2. Prueba Manual con cURL / Postman

1. Autenticar y obtener cookie de sesión:
```bash
curl -X POST http://localhost:8069/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "params": {"db": "v17", "login": "admin", "password": "admin"}}' \
  -c cookies.txt
```

2. Consultar productos con filtros:
```bash
# Todos los productos vendibles
curl -b cookies.txt http://localhost:8069/api/v1/products

# Solo productos con stock disponible
curl -b cookies.txt "http://localhost:8069/api/v1/products?only_stock=true"

# Probar validación de error 422
curl -b cookies.txt "http://localhost:8069/api/v1/products?updated_since=fecha_invalida"
```

---

## Supuestos y Limitaciones

- **Tramo A:** La consulta devuelve productos de tipo variante (`product.product`). Solo se muestran productos con `sale_ok=True` y `active=True`.
- En caso de entornos sin gestión avanzada de inventario multialmacén, `qty_available` refleja la suma global de inventario disponible de la compañía activa.

