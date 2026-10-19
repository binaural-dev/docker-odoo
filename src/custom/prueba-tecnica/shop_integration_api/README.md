# Shop Integration API (`shop_integration_api`)

API REST para la sincronización de catálogo de productos e ingreso de pedidos de venta desde una tienda en línea externa hacia Odoo 19.

## Tramos completados
- **Tramo A:** Endpoint `GET /api/v1/products` con autenticación `'user'`. Soporte de filtros individuales y combinados (`category_id`, `only_stock`, `modified_since`). Control estricto de errores de formato en fechas retornando HTTP 400 sin colapsar en error 500.
- **Tramo B:** Autenticación por cabecera `Authorization: Bearer <token>` validada contra el modelo nativo `res.users.apikeys` (scope `rpc`). Endpoint `POST /api/v1/orders` con validación de RIF de cliente, existencia de productos y cantidades positivas con respuestas uniformes HTTP 422. Modelo de auditoría `shop.api.log` que registra endpoint, usuario, estado HTTP y duración, resguardando la confidencialidad (no almacena tokens ni claves).
- **Tramo C (Parcial):** Idempotencia mediante cabecera `Idempotency-Key` en `POST /api/v1/orders`. Reintentos con idéntico payload retornan la misma respuesta previa (HTTP 201); reintentos con la misma clave pero cuerpo diferente retornan HTTP 409 Conflict. Vistas de interfaz en **Ajustes › Técnico** para auditoría y claves de idempotencia.

## Especificación de la API

### 1. `GET /api/v1/products`
Retorna productos vendibles y activos con su stock disponible.
* **Autenticación:** Sesión de usuario activa (`auth='user'`).
* **Parámetros de consulta (Query params):**
  * `category_id` *(int o string)*: ID o coincidencia en nombre de categoría.
  * `only_stock` *(bool)*: `true` o `1` para listar solo productos con `qty_available > 0`.
  * `modified_since` *(ISO-8601)*: Filtro por `write_date >= fecha` (ej. `2026-10-01`).

### 2. `POST /api/v1/orders`
Crea pedidos de venta en Odoo a partir de datos del e-commerce.
* **Autenticación:** Cabecera `Authorization: Bearer <api_key_de_odoo>`.
* **Cabeceras opcionales:** `Idempotency-Key: <uuid_o_hash>`.
* **Payload esperado:**
  ```json
  {
    "rif": "J-12345678-0",
    "client_order_ref": "TIENDA-ORD-9821",
    "lines": [
      {
        "default_code": "LAP-001",
        "quantity": 2
      }
    ]
  }
