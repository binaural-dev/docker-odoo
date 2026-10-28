# Prueba técnica — Desarrollador Odoo

Esta carpeta es el directorio de addons de la prueba. Aquí van **todos los módulos que entregues**
(`shop_integration_api`, `fleet_inspection` ya migrado, `sale_commission` corregido y `payment_request`).

| Carpeta | Qué contiene |
|---|---|
| `src/custom/prueba-tecnica/sale_commission` | Módulo en producción del **Ejercicio 3** (ticket urgente). Revisa su historial con `git log -- src/custom/prueba-tecnica/sale_commission`. |
| `src/custom/prueba-tecnica-odoo16/fleet_inspection` | Módulo del **Ejercicio 2**, escrito para **Odoo 16**. Está fuera del directorio de addons a propósito: con su versión `16.0.x` impediría arrancar Odoo 17 o superior. El primer paso de la migración es moverlo a `src/custom/prueba-tecnica/`. |

## Levantar el entorno

1. Copia `instances.example.jsonc` a `instances.json` y agrega una instancia que use esta carpeta como addons
   (cambia la versión por la que elijas: 17.0, 18.0 o 19.0):

   ```jsonc
   "prueba-tecnica": {
     "odoo_version": "18.0",
     "external_port": 8069,
     "database": "pg16",
     "odoo_config": "18.0_default",
     "overwrite_odoo_config": {
       "addons": ["src/custom/prueba-tecnica"],
       "dev_mode": true
     }
   }
   ```

   La instancia necesita una entrada en `odoo_configs` para su versión y una en `databases`
   (puedes partir de las del ejemplo). No necesitas Odoo Enterprise.

2. Construye y levanta: `./odoo build` y `./odoo start`.
3. Corre las pruebas: `./odoo test prueba-tecnica sale_commission` (varios módulos separados por coma).

Más detalles del CLI en el `readme.md` de la raíz del repositorio.
