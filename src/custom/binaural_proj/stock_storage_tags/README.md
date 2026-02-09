# Stock Storage Tags

Módulo para asignar etiquetas dinámicas de almacenamiento a productos, mejorando la organización en almacenes.

## Características

- **Etiquetas de Almacenamiento** con nombre, color y descripción
- Relación many2many entre productos y etiquetas
- Vista Kanban agrupada por etiquetas
- **Acción rápida** para asignar/quitar etiquetas masivamente

## Configuración

### 1. Crear Etiquetas

1. Ir a **Inventario → Configuración → Storage Tags**
2. Crear etiquetas (ej: "Frágil", "Pesado", "Refrigerado")
3. Asignar color para identificación visual

### 2. Asignar Etiquetas a Productos

**Opción A - Desde el producto:**
1. Ir a **Inventario → Productos → Productos**
2. Abrir un producto
3. En el campo **Storage Tags**, agregar etiquetas

**Opción B - Acción rápida (masivo):**
1. En la lista de productos, seleccionar varios productos
2. Ir a **Acción → Add Storage Tag**
3. Seleccionar etiquetas a agregar/quitar
4. Aplicar

## Vistas Disponibles

| Vista | Ubicación |
|-------|-----------|
| **Kanban por Etiquetas** | Inventario → Products by Storage Tag |
| **Configuración de Etiquetas** | Inventario → Configuración → Storage Tags |

## Funcionamiento

- Los productos sin etiquetas aparecen en columna "Undefined"
- Se pueden filtrar y agrupar productos por etiqueta
- Las etiquetas se muestran con colores en todas las vistas

## Dependencias

- `stock`
- `product`
