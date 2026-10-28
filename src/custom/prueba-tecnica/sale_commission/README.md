# Comisiones de vendedores (`sale_commission`)

Calcula la comisión del vendedor en cada línea de pedido de venta y ofrece un análisis mensual por vendedor.

## Configuración

- **Porcentaje del vendedor:** Ajustes › Usuarios › pestaña *Comisiones* (solo gerentes de ventas).
- **Porcentaje por categoría (desde la 1.1):** Inventario/Ventas › Configuración › Categorías de producto,
  campo *Comisión (%)*. Si la categoría (o una categoría padre) tiene porcentaje, reemplaza al del vendedor.

## Cómo funciona

- Al confirmar el pedido se fija el porcentaje en cada línea y se calcula la comisión sobre el subtotal sin impuestos.
- El botón *Recalcular comisiones* del pedido vuelve a aplicar los porcentajes vigentes.
- Ventas › Reportes › *Comisiones*: tabla dinámica y gráfico por vendedor y mes. Cada vendedor ve solo lo suyo.

## Pruebas

```bash
./odoo test prueba-tecnica sale_commission
```

## Prueba técnica — Ejercicio 3 (ticket T-200)

Corrección en la rama `hotfix/T-200`. El detalle completo está en [INCIDENT.md](INCIDENT.md).

### Tramos completados

| Tramo | Estado | Dónde |
|---|---|---|
| A — reproducir, causa raíz, corrección y prueba | ✅ | INCIDENT §1–4. Commits `9a95e9d` [TEST] y `3dbd7a3` [FIX] |
| B — contención, commit culpable, despliegue y mensaje al cliente | ✅ | INCIDENT §5 |
| C — impacto en los datos, script de solo lectura, mismo patrón y prevención | ✅ | INCIDENT §6, `scripts/`. Commits `d763732` [TEST], `5bdec31` [FIX] y `367c717` |

### Cómo probarlo

- Pruebas automáticas: `./odoo test prueba-tecnica sale_commission`. Las pruebas `test_t200_*` corren como
  vendedor o como gerente, no como administrador. Antes de las correcciones fallan 3: dos con `AccessError` y
  una con `12.0 != 5.0`.
- A mano: con un usuario que solo tenga *Ventas › Usuario: solo sus documentos*, crear y confirmar una
  cotización propia.
- Script de registros afectados: ver INCIDENT §6.2. Para tener datos de prueba,
  `odoo shell ... < scripts/t200_seed_incident.py` sobre una base de pruebas recién creada.

### Supuestos

- El vendedor puede **leer** los porcentajes por categoría (son las condiciones de su propia comisión). Si el
  cliente no lo quiere, la alternativa es un `sudo()` acotado y documentado en `_get_commission_percent()`.
- El porcentaje de respaldo es el del vendedor del pedido (`order_id.user_id`), como en la 1.0.0, y no el de
  quien confirma.
- Hora del despliegue de la 1.1.0 para el script: 12:00 m. hora de Venezuela (16:00 UTC) del día del ticket.

### Limitaciones conocidas

- `action_recompute_commissions()` sigue con una lógica distinta a la de la confirmación (solo categoría
  exacta) y su botón lo ve cualquier usuario. Queda documentado como ticket aparte en INCIDENT §6.4; no se tocó
  para no ampliar el hotfix.
- `sale.commission.rule` no tiene regla de registro multicompañía (INCIDENT §6.4).
- El plan de corrección de datos (INCIDENT §6.3) está escrito y el script de solo lectura está probado sobre
  datos simulados. El fragmento que corrige las líneas no se ejecutó contra una base real del cliente.
