# Stock Critical Alerts

Módulo para generar alertas cuando el stock de un producto cae por debajo de un umbral configurable.

## Características

- Campo **Stock Mínimo** en productos
- Alertas automáticas vía cron (cada hora)
- Notificaciones a administradores de inventario
- Dashboard con productos críticos agrupados por categoría

## Configuración

### 1. Establecer Stock Mínimo

1. Ir a **Inventario → Productos → Productos**
2. Abrir un producto de tipo "Almacenable"
3. En la pestaña **Inventario**, configurar el campo **Stock Mínimo**

### 2. Permisos de Notificaciones

Las notificaciones se envían a usuarios del grupo **Administrador de Inventario** (`stock.group_stock_manager`).

Para recibir alertas:
1. Ir a **Ajustes → Usuarios**
2. Seleccionar el usuario
3. En **Inventario**, asignar nivel **Administrador**

## Dashboard

Acceder desde: **Inventario → Critical Stock**

Muestra productos con stock crítico (donde `stock_alert_sent = True`) agrupados por categoría.

## Funcionamiento

| Condición | Acción |
|-----------|--------|
| `qty_available < stock_minimum` | Envía alerta y marca `stock_alert_sent = True` |
| `qty_available >= stock_minimum` | Resetea `stock_alert_sent = False` |
| Stock baja nuevamente | Nueva alerta (no duplicados) |

