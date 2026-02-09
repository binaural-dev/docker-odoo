# Account Invoice Discount

Módulo para aplicar descuentos automáticos en facturas según el tipo de cliente configurado.

## Características

- **Tipos de Cliente** dinámicos (modelo configurable)
- **Reglas de Descuento** únicas por tipo de cliente
- Descuento automático en tiempo real al crear facturas
- Validación de monto mínimo para aplicar descuento
- Menú de configuración restringido a administradores

## Configuración

### 1. Crear Tipos de Cliente

1. Ir a **Facturación → Configuración → Customer Types**
2. Crear tipos (ej: VIP, Mayorista, Minorista)
3. Asignar código único a cada tipo

### 2. Crear Reglas de Descuento

1. Ir a **Facturación → Configuración → Discount Rules**
2. Crear regla con:
   - **Tipo de Cliente**: Seleccionar tipo
   - **Descuento (%)**: Porcentaje a aplicar
   - **Monto Mínimo**: Monto de factura requerido (0 = siempre aplica)

> **Nota**: Solo se permite una regla por tipo de cliente.

### 3. Asignar Tipo a Cliente

1. Ir a **Contactos → Contactos**
2. Abrir contacto
3. Asignar campo **Tipo de Cliente**

## Funcionamiento

| Condición | Acción |
|-----------|--------|
| Cliente con tipo + regla activa | Aplica descuento automáticamente |
| Monto factura < monto mínimo | No aplica descuento |
| Cliente sin tipo asignado | No aplica descuento |
| Tipo sin regla configurada | No aplica descuento |

## Permisos

El menú de configuración solo es visible para usuarios con grupo **Asesor de Facturación** (`account.group_account_manager`).

## Dependencias

- `account`
- `contacts`
