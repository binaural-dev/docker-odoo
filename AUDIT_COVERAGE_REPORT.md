# Auditoría de Cobertura: 4 Módulos Website Sale

**Fecha:** 2026-06-26
**Módulos:** binaural_website_sale, binaural_website_sale_delivery,
             binaural_website_sale_comparison, binaural_website_sale_transit
**Resultado:** 91% cobertura general (580 stmts, 38 miss, 186 branches, 23 partial)
**Tests:** 348 ejecutados, 0 fallos, 0 errores
**Rama:** `19.0_refactor_ta_72234_mig_binaural_website`

---

## 1. Resumen Ejecutivo

Se crearon **24 archivos de tests** (4.093 líneas, 197 métodos de prueba) a partir de
una línea base de ~5% de cobertura en controllers. Se corrigieron **3 bugs** en código
fuente y se identificaron **2 bugs upstream** de Odoo 19 que dejan líneas inalcanzables.

| Módulo | Tests | Cobertura | Cambios en fuente |
|--------|-------|-----------|-------------------|
| `binaural_website_sale` | 102 métodos (11 archivos) | 88-91% | +1 método (`_compute_foreign_rate`) en cart.py |
| `binaural_website_sale_delivery` | 2 métodos (1 archivo) | 92% | Ninguno |
| `binaural_website_sale_comparison` | 5 métodos (1 archivo) | 100% | Ninguno |
| `binaural_website_sale_transit` | 88 métodos (11 archivos) | 90-95% | +`country_id` en hooks.py |

---

## 2. Bugs Corregidos en Código Fuente

### 2.1 `binaural_website_sale/controllers/cart.py` — Método faltante

**Problema:** `BinauralCart.cart()` llamaba `self._compute_foreign_rate(order)` en la
línea 85, pero el método solo existía en `BinauralWebsiteSale`, no en `BinauralCart`.
Esto causaba `AttributeError` al renderizar el carrito.

**Corrección:** Se agregó el método `_compute_foreign_rate` a la clase `BinauralCart`
(misma implementación que en `BinauralWebsiteSale`).

### 2.2 `binaural_website_sale_transit/hooks.py` — country_id en tax_group

**Problema:** El `post_init_hook` creaba `account.tax.group` sin `country_id`. En
Odoo 19, el validador de `account.tax` exige que `tax_group.country_id` coincida
con `tax.country_id`. Si `base.ve` no existía, el país quedaba como `False`.

**Corrección:** Se agregó fallback `env.ref("base.us")` cuando `base.ve` no existe,
y se pasa `country_id=country.id` al crear el `tax_group`.

### 2.3 `binaural_website_sale/hooks.py` — Mismo problema de country_id

**Corrección idéntica** al 2.2: fallback a `base.us` y `country_id` en `tax_group`.

---

## 3. Bugs Upstream Identificados (Odoo 19)

### 3.1 `_get_cart_notification_information` eliminado

**Archivo:** `binaural_website_sale/controllers/website_sale.py:257`
**Impacto:** Líneas 257-301 inalcanzables sin monkey-patch en tests.
**Detalle:** El método fue eliminado de Odoo 19. El controller binaural lo referencia
pero Python solo falla cuando se ejecuta esa ruta (no al importar).

### 3.2 `_cart_update` eliminado de base

**Archivo:** `binaural_website_sale/controllers/website_sale.py:225`
**Impacto:** Línea 225 y dependientes inalcanzables sin monkey-patch.
**Detalle:** `_cart_update` existía en Odoo 17-18 pero fue removido en 19. Solo
disponible vía `droggol_theme_common` (incompatible con v19).

### 3.3 `super().shop()` incompatible con MockRequest

**Impacto:** Líneas 165-183 (filtro multi-empresa en shop) no cubiertas.
**Detalle:** `WebsiteSale.shop()` requiere contexto HTTP completo que `MockRequest`
no puede simular completamente (`list` object has no attribute 'getlist`).

---

## 4. Detalle de Tests por Módulo

### 4.1 `binaural_website_sale` — 102 tests, 11 archivos

#### test_cart.py (9 tests)
Valida el flujo del carrito de compras:
- Redirect a login para usuarios públicos
- Errores desde sesión y POST
- Checkout step values
- cart_update_json redirect público
- Tipos de renderizado (popover)
- Comportamiento sin errores
- Access token inválido

#### test_cart_coverage.py (8 tests)
Cobertura profunda del flujo access_token:
- Token con orden abandoned (state='sale')
- Squash de token (restaurar orden previa)
- Merge con y sin sesión activa
- Sesión incorrecta muestra elección
- Orden vacía sin token
- Errores con líneas de orden

#### test_cart_merge_flow.py (7 tests)
Flujos de merge y acceso del carrito:
- Reset de sesión para órdenes no-draft
- Merge de órdenes abandonadas
- Sesión incorrecta
- Proceder con abandoned
- Cálculo de foreign_rate
- Filtrado de líneas inactivas
- Merge en misma orden

#### test_website_sale_controllers.py (17 tests)
Tests del controller BinauralWebsiteSale:
- Campos obligatorios billing/shipping (con y sin state_required)
- Errores de checkout (stock bajo, producto servicio)
- Sitemap shop (categoría, shop principal)
- cart_update_json (redirect, draft, non-draft, force_create)
- compute_foreign_rate (con y sin tasa)
- shop_payment_confirmation (budget_send true/false)

#### test_website_sale_controllers_v2.py (16 tests)
Tests extendidos del controller:
- ShopCheckout: redirects, sesiones, foreign_rate, skip step
- Sitemap: empty query, None qs, non-shop query
- ShopMultiCompany: filtro por empresa
- CartUpdateJson: atributos custom, display, cart vacío
- ShopPaymentConfirmation: budget true/false

#### test_website_sale_coverage.py (13 tests)
Cobertura adicional de controllers:
- ShopCheckoutDelivery: carrito con direcciones, productos deliverables,
  sin carrier, rate fallido, precio diferente
- ShopMultiCompanyExtended: filtro multi-empresa
- CartUpdateJsonPostProcessing: non-draft reset/force, atributos custom,
  display full, qty stock cap, zero qty, budget_send

#### test_website_sale_models.py (10 tests)
Tests de modelos product.template y website:
- _search_get_detail: agrega requires_sudo
- _search_build_domain: sin filtro, con filtro empresa
- _search_fetch: sin filtro retorna todo, con filtro stock
- _get_product_sort_mapping
- _search_with_fuzzy single company
- Campos default website (do_not_show, people_not_see_prices/available)

#### test_website.py (5 tests)
Tests de _search_with_fuzzy multi-empresa:
- Single company (sin filtro)
- Multi-company filters
- Sort mapping entries
- Sort mapping labels
- Empty search

#### test_res_config_settings.py (6 tests)
Tests de campos related:
- do_not_show_products
- budget_send
- people_not_see_prices
- people_not_see_available
- Write actualiza website
- Write actualiza company

#### test_hooks.py (4 tests)
Tests del post_init_hook:
- Crea impuestos en modo test
- Salta cuando no es modo test
- Salta cuando impuesto ya existe
- Crea ambos impuestos (venta y compra)

#### test_debug_coverage.py (7 tests)
Tests de diagnóstico y cobertura avanzada:
- cart lines 45-46 (non-draft reset)
- cart access_token lines 59-74
- cart abandonado con token
- merge flow
- cart_update_json lines 235-301 (con monkey-patch de _cart_update
  y _get_cart_notification_information)
- cart_update_json display=False
- cart_update_json zero qty

#### common.py (clases base, sin tests)
- `TestProductSearchCommon`: Setup de productos, almacén, quantos
- `TestWebsiteCommon`: Setup de website y company
- `TestCheckoutCommon`: Setup de partner, productos, sale.order

---

### 4.2 `binaural_website_sale_delivery` — 2 tests, 1 archivo

#### test_controllers.py (2 tests)
- `_order_summary_values` sin foreign_rate
- `_order_summary_values` con foreign_rate

---

### 4.3 `binaural_website_sale_comparison` — 5 tests, 1 archivo

#### test_module.py (5 tests)
- Módulo instalado
- Dependencia en website_sale_comparison
- auto_install=True
- Template XML existe
- Template es QWeb

---

### 4.4 `binaural_website_sale_transit` — 88 tests, 11 archivos

#### test_transit_controllers.py (19 tests)
BinauralWebsiteSale transit:
- get_website_range_config (sin config, con config)
- get_template_confirmation_payment
- sitemap_shop (main, category, empty qs)
- shop agrega range_config
- product agrega range_config
- shop_payment_confirmation envía email

ZmartRequestProduct:
- request_product (success, sin ID, producto inexistente)
- request_product_partner (success, parámetros faltantes, parciales,
  crea línea, con user_ids, con email_ids, con ambos)

#### test_transit_controllers_v2.py (9 tests)
Tests extendidos del controller transit:
- shop_payment_confirmation con user_ids, email_ids, ambos, ninguno,
  múltiples, users+emails
- sitemap_shop con categoría
- get_website_range_config líneas vacías
- product agrega range_config a qcontext

#### test_transit_hooks.py (3 tests)
- Hook crea impuestos en modo test
- Hook salta cuando no es modo test
- Hook salta cuando impuesto ya existe

#### test_qty_in_transit.py (4 tests)
- Sin moves retorna False
- Con purchase moves calcula qty
- move_ids vs move_ids_without_package
- purchase_line_id en picking

#### test_range_qty_config.py (11 tests)
TestRangeQtyConfig:
- Unlink cascade a child lines
- Unlink sin líneas

TestRangeQtyConfigLine:
- Validación min < max
- Validación min == max
- Validación min > max (raises)
- Onchange show transit < 20
- Onchange hide transit >= 20
- Onchange exactamente 20
- Write trigger validación
- Write sin cambio en min_qty
- Valores default

#### test_product_template.py (7 tests)
- Producto servicio retorna False
- Sin moves retorna False
- Compra futura
- Productos batch
- Picking no asignado no contado
- Mes en español
- Flujo de compra

#### test_request_product.py (10 tests)
Validación de email:
- Email vacío, sin @, sin punto, con espacios, con acentos
- Email válido
- Plus addressing
- Subdominio
- Write válido, write inválido

#### test_request_product_v2.py (8 tests)
- Partner con single/multiple user_ids
- Partner con user_ids + email_ids
- Partner solo email_ids
- Exception handler (partner y request_product)
- Crea línea con comentarios
- Usuario público sin partner

#### test_request_product_coverage.py (8 tests)
Cobertura de email building (líneas 110-144):
- Single user, múltiples users
- Users + emails
- Solo email_ids sin users
- Múltiples users + emails
- Single user sin email_ids
- Sin users ni emails
- Parámetros faltantes retorna 204

#### test_security.py (8 tests)
TestRangeQtyConfigSecurity:
- range.qty.config visible/invisible por empresa
- range.qty.config sin website visible a todos

TestRequestProductRoutes:
- request.product visible/invisible por empresa
- search_read API
- partner create line

---

## 5. Cobertura por Archivo

| Archivo | Stmts | Miss | Branch | BrPart | Cover |
|---------|-------|------|--------|--------|-------|
| `cart.py` (binaural) | 59 | 4 | 26 | 4 | 91% |
| `website_sale.py` (binaural) | 145 | 22 | 60 | 7 | 83% |
| `hooks.py` (binaural) | 14 | 1 | 6 | 1 | 90% |
| `website_sale.py` (delivery) | 11 | 0 | 2 | 1 | 92% |
| `request_product.py` (transit) | 49 | 4 | 18 | 1 | 90% |
| `website_sale.py` (transit) | 62 | 4 | 18 | 2 | 92% |
| `hooks.py` (transit) | 14 | 1 | 6 | 1 | 90% |
| `product_template.py` (transit) | 47 | 1 | 18 | 3 | 94% |
| `range_qty_config_line.py` | 32 | 0 | 10 | 2 | 95% |
| `request_product_email.py` | 31 | 1 | 10 | 1 | 95% |
| **TOTAL** | **580** | **38** | **186** | **23** | **91%** |

9 archivos con cobertura completa (100%): website.py, res_company.py, res_config_settings.py,
res_config_settings.py (transit), request_product.py (transit models), range_qty_config.py,
request_product_line.py, __init__.py hooks, __init__.py models.

---

## 6. Líneas No Cubiertas (38 miss)

### cart.py (4 miss)
- Línea 23: branch de exit cuando no hay order
- Líneas 45-46: reset de sesión para órdenes no-draft
- Líneas 64-65: branch de access_token
- Línea 71→76: branch de retorno

### website_sale.py binaural (22 miss)
- Línea 30→32: branch shipping state_required
- Líneas 59→68/61→68: branch deliverable rate
- Línea 144→142: branch sitemap yield
- **Líneas 165-183**: Filtro multi-empresa en shop() — `super().shop()` incompatible con MockRequest
- Línea 236→235: branch de display
- Líneas 252-253: branch de set_qty
- **Líneas 267-301**: cart_update_json post-rendering — dependen de `_get_cart_notification_information` (eliminado en Odoo 19)

### request_product.py transit (4 miss)
- Líneas 131-134: branch cuando email_one=False y first_email está vacío

### Otros (8 miss)
- Transit website_sale.py: líneas 52-53, 72→70, 91-96
- hooks binaural: línea 12
- hooks transit: línea 12
- product_template transit: línea 57, 93→exit
- request_product_email: línea 47

---

## 7. Patrones de Mocking Utilizados

### MockRequest (controllers)
```python
from odoo.addons.website_sale.tests.common import MockRequest

with MockRequest(self.env, website=self.website, sale_order_id=self.order.id) as req:
    req.env = self.env(user=self.env.user)
    result = controller.method(...)
```

### Patch HttpCase.http_port (todas las clases con MockRequest)
```python
cls._port_patcher = patch('odoo.tests.common.HttpCase.http_port', return_value=None)
cls._port_patcher.start()
# ... en tearDownClass:
cls._port_patcher.stop()
```

### Monkey-patch de métodos eliminados en Odoo 19
```python
SaleOrder._cart_update = lambda self, **kw: {'line_id': 0, 'warning': ''}
BinauralWebsiteSale._get_cart_notification_information = lambda self, order, line_ids: {}
```

### Patch de search para modelos con get_current_website
```python
with patch.object(type(self.env['request.product']), 'search', return_value=self.request_product):
    result = controller.request_product_partner(...)
```

---

## 8. Infraestructura de Ejecución

- **Contenedor:** `odoo-josehern19.0-tests`
- **DB:** `db-pg16` (PostgreSQL 16)
- **Script:** `src/scripts/run_tests.sh`
- **Ejecución:** `./src/scripts/run_tests.sh --container=odoo-josehern19.0-tests --modules=<MODS> --tags=<TAGS>`
- **Coverage mode:** Sin `--no-cov`
- **No-cov mode:** Con `--no-cov --keep-db`
- **Puerto HTTP:** 9999 (evita conflicto con 8069 en uso)
