# Account Financial KPI

Módulo para crear un tablero con indicadores de salud financiera de la empresa, con visualización tipo semáforo.

## Características

- **Modelo `account.financial.kpi`** configurable
- Fórmulas Python personalizables sobre cuentas contables
- Sistema de umbrales con semáforos (verde/amarillo/rojo)
- **Dashboard Kanban** con visualización de estado
- 3 KPIs de ejemplo precargados

## Configuración

### 1. Ver Dashboard

1. Ir a **Facturación → Financial Health**
2. Se muestra vista Kanban con tarjetas de KPIs
3. Cada tarjeta muestra: nombre, valor, estado (badge de color)

### 2. Configurar KPIs

1. Ir a **Facturación → Configuración → Financial KPIs**
2. Crear o editar un KPI con:
   - **Nombre**: Identificador del indicador
   - **Fórmula**: Expresión Python
   - **Umbral Advertencia**: Valor límite para estado amarillo
   - **Umbral Crítico**: Valor límite para estado rojo
   - **Invertir Umbrales**: Si se activa, valores altos son críticos

### 3. Variables Disponibles en Fórmulas

| Variable | Descripción |
|----------|-------------|
| `total_income` | Total de ingresos |
| `total_expense` | Total de gastos |
| `total_assets` | Total de activos |
| `total_liabilities` | Total de pasivos |
| `total_receivable` | Cuentas por cobrar |
| `total_payable` | Cuentas por pagar |
| `total_equity` | Patrimonio |
| `total_current_assets` | Activos corrientes |
| `total_current_liabilities` | Pasivos corrientes |

## KPIs de Ejemplo

| KPI | Fórmula | Umbrales |
|-----|---------|----------|
| Margen Bruto | `(total_income - total_expense) / total_income * 100` | Adv: 30%, Crít: 15% |
| Liquidez Corriente | `total_current_assets / total_current_liabilities` | Adv: 1.5, Crít: 1.0 |
| Rotación CxC | `total_income / total_receivable` | Adv: 4, Crít: 2 |

## Funcionamiento Semáforos

| Estado | Condición (normal) | Condición (invertido) |
|--------|--------------------|-----------------------|
| Verde | Valor > Umbral Advertencia | Valor < Umbral Advertencia |
| Amarillo | Valor entre umbrales | Valor entre umbrales |
| Rojo | Valor < Umbral Crítico | Valor > Umbral Crítico |

## Dependencias

- `account`
