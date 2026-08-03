# Skill: odoo-purge-localization

## Propósito
Desinstalar de forma segura localizaciones pesadas (como Binaural) en Odoo 17.0+, evitando timeouts de base de datos y errores de vistas de Studio, garantizando que la BD nativa pueda montarse sin errores en cualquier ambiente.

## Cuándo usar
- Cuando el cliente quiere volver a Odoo Nativo/USD.
- Cuando la desinstalación normal falla por timeouts o errores XML.
- Cuando hay cientos de vistas de Studio rompiendo el sistema tras quitar un módulo.
- Cuando se necesita purga selectiva (conservar uno o más módulos de la localización).

---

## Configuración

Antes de ejecutar cualquier script, definir y reemplazar estas variables en todos los comandos SQL. **Esta skill es genérica — nunca hardcodear nombres de módulos de un cliente puntual directamente en el SQL; usar siempre estas variables.**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `{MODULE_PREFIX}` | Prefijo de módulos a purgar | `binaural_` |
| `{MODULOS_CONSERVAR}` | Lista de módulos a NO purgar, entre comillas simples y separados por coma | `'binaural_seller','binaural_brand'` |
| `{MODULOS_CUSTOM_SAGRADOS}` | Módulos custom del cliente (no nativos de Odoo) que deben tratarse igual que los nativos: nunca desactivar sus vistas ni tocar sus datos. Se arma por proyecto durante la Fase 0 | `'cliente_seller_brand','cliente_stock_lot'` |

Para purga total (todos los módulos), usar `{MODULOS_CONSERVAR}` = `''` (cadena vacía para que `NOT IN ('')` no excluya nada).

### Fase 0 — Detectar módulos custom sagrados del proyecto

Antes de tocar nada, listar los módulos custom instalados que **no** pertenecen a `{MODULE_PREFIX}` y que el cliente quiere conservar intactos (ej. módulos propios del cliente para su marca/negocio). Esta lista se guarda en `{MODULOS_CUSTOM_SAGRADOS}` y se usa en la Fase 2. Nunca asumir los módulos de un proyecto anterior — se detectan de nuevo en cada ejecución.

```sql
SELECT name, state FROM ir_module_module
WHERE state = 'installed'
  AND name NOT LIKE '{MODULE_PREFIX}%'
  AND name NOT IN (SELECT name FROM ir_module_module WHERE name IN (
      -- lista de módulos nativos de Odoo conocidos, para excluirlos de esta revisión manual
      'base','web','mail','account','account_accountant','account_payment',
      'sale','sale_management','sale_stock','purchase','purchase_stock',
      'stock','stock_account','product','hr','hr_attendance',
      'point_of_sale','pos_sale','pos_hr','pos_enterprise','pos_discount','pos_iot','pos_online_payment',
      'delivery','portal','digest','crm','helpdesk','documents',
      'contacts_enterprise','partner_autocomplete','sales_team','payment'
  ));
```

Revisar el resultado con el consultor/cliente y confirmar cuáles deben quedar en `{MODULOS_CUSTOM_SAGRADOS}`.

---

## Checklist Pre-Purga

Ejecutar en orden y verificar cada ítem antes de continuar:

- [ ] **Backup completo** de la base de datos (`pg_dump` o snapshot).
- [ ] **Nadie conectado**: matar conexiones activas excepto la propia.
- [ ] **Cron jobs desactivados**: `UPDATE ir_cron SET active = false;`
- [ ] **Scheduled actions desactivadas**: `UPDATE ir_act_server SET active = false;`
- [ ] **Odoo en maintenance mode** o detenido (nunca correr estos scripts con Odoo en producción).
- [ ] **Identificar módulos a conservar** y verificar que compilan sin dependencias a los módulos purgados.
- [ ] **Fase 0 completada**: `{MODULOS_CUSTOM_SAGRADOS}` definida y confirmada con el cliente.

---

## Procedimiento Maestro

Las fases deben ejecutarse en este orden exacto. Cada fase incluye el SQL concreto.

### Fase 1 — Anular FKs desde tablas nativas hacia tablas de la localización

**Objetivo:** Romper referencias desde tablas nativas (ej. `account_move`) hacia tablas de los módulos a purgar, preservando la data nativa (el registro se conserva, solo se anula la FK). Solo anula FKs que apuntan a modelos definidos exclusivamente por `{MODULE_PREFIX}`, ignorando modelos nativos que la localización solo extendió (`_inherit` sin `_name`).

```sql
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT
            tc.table_name AS tabla_nativa,
            kcu.column_name AS columna_fk,
            ccu.table_name AS tabla_custom
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name NOT IN (
              SELECT REPLACE(m.model, '.', '_')
              FROM ir_model_data md
              JOIN ir_model m ON (md.res_id = m.id AND md.model = 'ir.model')
              WHERE md.module LIKE '{MODULE_PREFIX}%'
                AND md.module NOT IN ({MODULOS_CONSERVAR})
          )
          AND ccu.table_name IN (
              SELECT REPLACE(m.model, '.', '_')
              FROM ir_model_data md
              JOIN ir_model m ON (md.res_id = m.id AND md.model = 'ir.model')
              WHERE md.module LIKE '{MODULE_PREFIX}%'
                AND md.module NOT IN ({MODULOS_CONSERVAR})
          )
    LOOP
        EXECUTE format(
            'UPDATE %I SET %I = NULL WHERE %I IS NOT NULL',
            r.tabla_nativa, r.columna_fk, r.columna_fk
        );
        RAISE NOTICE 'FK anulada: %.% -> %', r.tabla_nativa, r.columna_fk, r.tabla_custom;
    END LOOP;
END $$;
```

---

### Fase 2 — Protección de vistas y desactivación de vistas de la localización

**Regla de oro:** las vistas base (`inherit_id IS NULL`) y las de módulos nativos o de `{MODULOS_CUSTOM_SAGRADOS}` **nunca** se desactivan — se reactivan explícitamente antes de tocar nada más, por si quedaron desactivadas de una purga anterior o de Studio.

**Bloque A: reactivar vistas nativas, base y custom sagradas**

```sql
UPDATE ir_ui_view v SET active = true FROM ir_model_data md
WHERE v.id = md.res_id AND md.model = 'ir.ui.view'
AND md.module IN (
    'base','web','mail','account','account_accountant','account_payment',
    'sale','sale_management','sale_stock','purchase','purchase_stock',
    'stock','stock_account','product','hr','hr_attendance',
    'point_of_sale','pos_sale','pos_hr','pos_enterprise','pos_discount','pos_iot','pos_online_payment',
    'delivery','portal','digest','crm','helpdesk','documents',
    'contacts_enterprise','partner_autocomplete','sales_team','payment',
    {MODULOS_CUSTOM_SAGRADOS}
);

UPDATE ir_ui_view SET active = true WHERE inherit_id IS NULL;
```

**Bloque B: desactivar vistas (extensiones `inherit_id IS NOT NULL`) que pertenecen a los módulos a purgar**

```sql
UPDATE ir_ui_view
SET active = false
WHERE active = true
  AND inherit_id IS NOT NULL
  AND id IN (
      SELECT res_id FROM ir_model_data
      WHERE model = 'ir.ui.view'
        AND module LIKE '{MODULE_PREFIX}%'
        AND module NOT IN ({MODULOS_CONSERVAR})
  );
```

**Bloque C: vistas de Studio (sin registro en ir_model_data)**

```sql
UPDATE ir_ui_view
SET active = false
WHERE active = true
  AND id NOT IN (SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.view');
```

**Bloque D: vistas no nativas que referencian campos custom (`x_` o campos de la localización)**

```sql
WITH campos_a_purgar AS (
    SELECT f.name AS campo
    FROM ir_model_fields f
    JOIN ir_model_data md ON md.model = 'ir.model.fields' AND md.res_id = f.id
    WHERE md.module LIKE '{MODULE_PREFIX}%'
      AND md.module NOT IN ({MODULOS_CONSERVAR})
)
UPDATE ir_ui_view v
SET active = false
WHERE v.active = true
  AND v.id NOT IN (
      SELECT res_id FROM ir_model_data
      WHERE model = 'ir.ui.view'
        AND module IN ('base', 'web', 'stock', 'product', 'account',
                       'sale', 'purchase', 'mail', 'crm', 'hr', 'mrp',
                       'stock_account', 'delivery', 'uom', 'analytic', 'resource')
  )
  AND EXISTS (
      SELECT 1 FROM campos_a_purgar c
      WHERE v.arch_db::text ILIKE '%' || c.campo || '%'
  );
```

**Bloque E: purgar vistas de Studio propiamente dichas**

Las vistas creadas por Studio (módulo `studio_customization`) suelen referenciar campos `x_` que dependen de modelos de `{MODULE_PREFIX}` y producen errores `field is undefined` en el frontend si no se limpian.

```sql
DELETE FROM ir_ui_view v WHERE v.id IN (
    SELECT v2.id FROM ir_ui_view v2
    JOIN ir_model_data md ON (md.res_id = v2.id AND md.model = 'ir.ui.view')
    WHERE md.module = 'studio_customization'
);
DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND module = 'studio_customization';
```

---

### Fase 3 — Purgar Record Rules de los módulos a eliminar

**Objetivo:** Eliminar reglas de acceso (ir.rule) que pertenecen a los módulos a purgar. Si no se hace antes de borrar `ir_model_data`, quedan huérfanas y producen `KeyError: company_id`.

```sql
DELETE FROM ir_rule
WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE model = 'ir.rule'
      AND module LIKE '{MODULE_PREFIX}%'
      AND module NOT IN ({MODULOS_CONSERVAR})
);
```

---

### Fase 4 — Purga de Metadatos y Módulos

**Objetivo:** Eliminar los registros en `ir_model_data` e `ir_module_module` para que Odoo olvide los módulos. Marcar como `uninstallable` en vez de solo borrar el registro evita que Odoo intente reconocerlos o reinstalarlos si siguen presentes en el `addons_path`.

> **ADVERTENCIA:** Este paso generará FK huérfanas en tablas como `account_move_account_move_send_rel`, `mail_compose_message_*`, etc. La Fase 7 existe precisamente para limpiarlas. Si se omite, Odoo fallará con `IntegrityError`.

```sql
-- Primero los datos de módulo (dependencias de otros registros)
DELETE FROM ir_model_data
WHERE module LIKE '{MODULE_PREFIX}%'
  AND module NOT IN ({MODULOS_CONSERVAR});

-- Luego el módulo en sí: uninstallable en vez de DELETE, para que Odoo lo ignore
-- físicamente aunque la carpeta siga en el addons_path
UPDATE ir_module_module
SET state = 'uninstallable'
WHERE name LIKE '{MODULE_PREFIX}%'
  AND name NOT IN ({MODULOS_CONSERVAR});

DELETE FROM ir_model_data
WHERE module = 'base'
  AND name LIKE 'module_' || '{MODULE_PREFIX}%'
  AND name NOT IN ({MODULOS_CONSERVAR});
```

---

### Fase 5 — Limpieza de Dependencias

```sql
DELETE FROM ir_module_module_dependency
WHERE name LIKE '{MODULE_PREFIX}%'
  AND name NOT IN ({MODULOS_CONSERVAR});
```

---

### Fase 6 — Corregir FK huérfanas (genérico, cubre cualquier tabla `_rel`)

**Objetivo:** eliminar registros en tablas relacionales que referencian filas ya inexistentes, y anular (no borrar) FKs huérfanas en tablas de negocio nativas (`account_move`, `sale_order`, etc.) para no perder esos registros.

> **NOTA SOBRE DATA NATIVA:** Para las tablas core listadas abajo se hace `UPDATE ... SET col = NULL`, nunca `DELETE`. Para el resto (tablas `_rel`, huérfanas puramente relacionales) se hace `DELETE` porque son filas de relación sin identidad propia.

**Ejecutar al menos 2 veces** (la primera pasada puede exponer nuevos huérfanos en cascada, especialmente en tablas `_rel` sin FK formal que dependan de otras que sí se limpiaron):

```sql
DO $$ DECLARE fk RECORD; BEGIN
    FOR fk IN
        SELECT conrelid::regclass::text AS src,
               (SELECT attname FROM pg_attribute WHERE attrelid = conrelid AND attnum = conkey[1]) AS col,
               confrelid::regclass::text AS ref,
               (SELECT attname FROM pg_attribute WHERE attrelid = confrelid AND attnum = confkey[1]) AS rcol
        FROM pg_constraint
        WHERE contype = 'f' AND confrelid::regclass::text NOT LIKE 'ir\_%'
    LOOP
        IF fk.src IN ('account_move', 'account_move_line', 'sale_order', 'sale_order_line',
                      'purchase_order', 'purchase_order_line', 'res_partner',
                      'product_template', 'product_product') THEN
            EXECUTE format(
                'UPDATE %I SET %I = NULL WHERE %I NOT IN (SELECT %I FROM %I)',
                fk.src, fk.col, fk.col, fk.rcol, fk.ref
            );
        ELSE
            EXECUTE format(
                'DELETE FROM %I WHERE %I IS NOT NULL AND NOT EXISTS (SELECT 1 FROM %I WHERE %I = %I.%I)',
                fk.src, fk.col, fk.ref, fk.rcol, fk.src, fk.col
            );
        END IF;
    END LOOP;
END $$;
```

> Si durante la Fase 10 (sync) aparecen `IntegrityError` en tablas `_rel` puntuales que la query anterior no cubrió (esto pasa con relaciones many2many que Odoo creó sin FK formal a nivel de Postgres), identificarlas desde el traceback y agregar un `DELETE` puntual para esa tabla exacta antes de reintentar el sync — no dejarlo como parte fija de esta skill, porque son específicas de cada proyecto.

---

### Fase 7 — Limpieza de otros registros huérfanos

La purga de `ir_model_data` deja huérfanos en tablas que no tienen FK formal pero sí dependencia lógica.

**7a. Traducciones de módulos purgados**

```sql
DELETE FROM ir_translation
WHERE module IS NOT NULL
  AND module LIKE '{MODULE_PREFIX}%'
  AND module NOT IN ({MODULOS_CONSERVAR});
```

**7b. Propiedades (ir_property) huérfanas**

```sql
DELETE FROM ir_property
WHERE fields_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM ir_model_fields f WHERE f.id = ir_property.fields_id);
```

**7c. Acciones ventana (ir_act_window) que apuntan a modelos inexistentes**

```sql
DELETE FROM ir_act_window
WHERE res_model IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM ir_model m WHERE m.model = ir_act_window.res_model);
```

**7d. Acciones URL y server actions huérfanas**

```sql
DELETE FROM ir_act_url
WHERE NOT EXISTS (SELECT 1 FROM ir_act_window a WHERE a.binding_model_id = ir_act_url.binding_model_id)
  AND binding_model_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM ir_model m WHERE m.id = ir_act_url.binding_model_id);

DELETE FROM ir_act_server
WHERE NOT EXISTS (SELECT 1 FROM ir_act_window a WHERE a.binding_model_id = ir_act_server.binding_model_id)
  AND binding_model_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM ir_model m WHERE m.id = ir_act_server.binding_model_id);
```

Si tras el sync (Fase 10) aparece un error tipo `Unexpected indentation` en server actions, es señal de una `ir.act.server` huérfana con código Python roto; se puede acotar la limpieza a los módulos nativos conocidos:

```sql
DELETE FROM ir_act_server
WHERE id NOT IN (
    SELECT res_id FROM ir_model_data
    WHERE model = 'ir.act.server'
      AND module IN ('base','mail','account','sale','purchase','stock','hr','product')
);
```

**7e. Menús huérfanos**

Los menús quedan sin registro en `ir_model_data` pero pueden seguir visibles en la UI. Se eliminan en orden: primero las hojas (sin hijos), luego los padres que quedaron sin hijos tras ese borrado. Ejecutar este mismo bloque 2-3 veces hasta que no borre filas (menús anidados requieren eliminación iterativa):

```sql
DELETE FROM ir_ui_menu WHERE id IN (
    SELECT m.id FROM ir_ui_menu m
    WHERE NOT EXISTS (SELECT 1 FROM ir_model_data md WHERE md.res_id = m.id AND md.model = 'ir.ui.menu')
    AND NOT EXISTS (SELECT 1 FROM ir_ui_menu child WHERE child.parent_id = m.id)
);
```

---

### Fase 8 — Sincronización

```bash
odoo -d <DB_NAME> -u base --workers=0 --max-cron-threads=0 --stop-after-init
```

- `--workers=0`: evita deadlocks en proceso de upgrade.
- `--max-cron-threads=0`: no ejecutar crons durante la sincronización.
- `--stop-after-init`: termina Odoo apenas termina el upgrade, no lo deja corriendo.

Si el log muestra que faltan acciones genéricas que vistas nativas esperan encontrar (ej. una `ir.act.window` con un ID fijo referenciado desde una vista XML nativa), identificar el ID y el modelo exactos desde el traceback y recrear el registro puntualmente — esto es específico de cada base y no debe generalizarse a un INSERT fijo en la skill.

---

### Fase 9 — Restaurar módulos al addons_path

- **NO eliminar las carpetas físicas** de los módulos del addons_path. La purga SQL es suficiente para que Odoo los ignore.
- Si se movieron temporalmente fuera del addons_path para evitar que `update_list()` los reinstale, **devolverlos** a su ubicación original tras completar la sincronización.

---

## Verificación Post-Purga

Ejecutar después de la sincronización para confirmar que la BD es funcional:

- [ ] Odoo arranca sin errores en el log (`INFO <db> odoo.modules.loading: Modules loaded.`).
- [ ] El menú principal carga sin errores XML.
- [ ] Abrir formularios clave: `account.move` (facturas), `sale.order` (ventas), `purchase.order` (compras), `res.partner` (contactos).
- [ ] Abrir formularios de los módulos listados en `{MODULOS_CUSTOM_SAGRADOS}` y confirmar que sus vistas y datos siguen intactos.
- [ ] Revisar el log en busca de `KeyError`, `IntegrityError`, `ViewError`.
- [ ] Si hay errores de assets/bundles: ejecutar también `odoo -d <DB_NAME> -u web --workers=0 --max-cron-threads=0 --stop-after-init`.

---

## Consideraciones para Purga Selectiva

Cuando el cliente quiere conservar uno o más módulos de la localización (ej. solo `binaural_seller`):

1. Definir `{MODULOS_CONSERVAR}` = `'binaural_seller'` (o los que apliquen).
2. Revisar el `__manifest__.py` de los módulos conservados: sus `depends` NO deben listar módulos que se van a purgar. Si lo hacen, ajustar el manifest antes.
3. Si un módulo conservado depende de otro que se purga, la purga selectiva fallará — primero hay que romper esa dependencia (extrayendo la funcionalidad necesaria a un módulo custom intermedio).
4. Los scripts de la Fase 1 (anular FKs) respetan esto porque excluyen tablas de modelos cuyo módulo está en `{MODULOS_CONSERVAR}`.

---

## Seguridad y Advertencias

- **Backup obligatorio.** No hay vuelta atrás sin él.
- **Nunca ejecutar con Odoo en producción.** Detener la instancia o poner en maintenance mode.
- **Las Fases son secuenciales y dependientes.** Saltarse una fase (especialmente la 6/7 después de la 4) deja la BD en estado inconsistente.
- **La data nativa (account.move, res.partner, sale.order, etc.) se preserva.** Los scripts están diseñados para solo eliminar metadatos, registros huérfanos y referencias rotas. Nunca se ejecuta un `DELETE` ni `TRUNCATE` sobre tablas de negocio nativas.
- **Excepción:** Si un módulo de la localización creó modelos propios (ej. `binaural_brand`) con datos, esos datos se conservan en la tabla física aunque Odoo ya no los reconozca. Si se desea eliminarlos, hacerlo manualmente con `DROP TABLE IF EXISTS` después de verificar que ninguna tabla nativa tiene FK hacia ellos (Fase 1 ya las anuló).
- Los módulos purgados pueden permanecer en el addons_path sin riesgo; Odoo simplemente los ignorará al no tener entrada en `ir_module_module`.
- **Nunca hardcodear en esta skill nombres de módulos, tablas o IDs de un proyecto puntual.** Si un cliente necesita un paso extra (una tabla `_rel` sin FK formal, una acción con ID fijo faltante, etc.), resolverlo puntualmente en la sesión de ese proyecto, no agregarlo permanentemente a este archivo — así la skill se mantiene reutilizable para cualquier cliente.
