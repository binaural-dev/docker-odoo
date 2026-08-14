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

Antes de ejecutar cualquier script, definir y reemplazar estas variables en todos los comandos SQL:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `{MODULE_PREFIX}` | Prefijo de módulos a purgar | `binaural_` |
| `{MODULOS_CONSERVAR}` | Lista de módulos a NO purgar, entre comillas simples y separados por coma | `'binaural_seller','binaural_brand'` |

Para purga total (todos los módulos), usar `{MODULOS_CONSERVAR}` = `''` (cadena vacía para que `NOT IN ('')` no excluya nada).

---

## Checklist Pre-Purga

Ejecutar en orden y verificar cada ítem antes de continuar:

- [ ] **Backup completo** de la base de datos (`pg_dump` o snapshot).
- [ ] **Nadie conectado**: matar conexiones activas excepto la propia.
- [ ] **Cron jobs desactivados**: `UPDATE ir_cron SET active = false;`
- [ ] **Scheduled actions desactivadas**: `UPDATE ir_act_server SET active = false;`
- [ ] **Odoo en maintenance mode** o detenido (nunca correr estos scripts con Odoo en producción).
- [ ] **Identificar módulos a conservar** y verificar que compilan sin dependencias a los módulos purgados.

---

## Procedimiento Maestro

Las fases deben ejecutarse en este orden exacto. Cada fase incluye el SQL concreto.

### Fase 1 — Anular FKs desde tablas nativas hacia tablas de la localización

**Objetivo:** Romper referencias desde tablas nativas (ej. `account_move`) hacia tablas de los módulos a purgar. Esto preserva la data nativa (el registro en `account_move` se conserva, solo se anula la FK).

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

### Fase 2 — Desactivar vistas de módulos a purgar y vistas de Studio

**Objetivo:** Desactivar preventivamente toda vista que pueda romper. Esto evita errores XML al montar la BD. Se desactivan en tres bloques:

**Bloque A: Vistas pertenecientes a los módulos a purgar**

```sql
UPDATE ir_ui_view
SET active = false
WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE model = 'ir.ui.view'
      AND module LIKE '{MODULE_PREFIX}%'
      AND module NOT IN ({MODULOS_CONSERVAR})
);
```

**Bloque B: Vistas de Studio (sin registro en ir_model_data)**

```sql
UPDATE ir_ui_view
SET active = false
WHERE active = true
  AND id NOT IN (SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.view');
```

**Bloque C: Vistas no nativas que referencian campos custom (x_ o campos de la localización)**

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

### Fase 4 — Purga de Metadatos

**Objetivo:** Eliminar los registros en `ir_model_data` e `ir_module_module` para que Odoo olvide los módulos.

> **ADVERTENCIA:** Este paso generará FK huérfanas en tablas como `account_move_account_move_send_rel`, `mail_compose_message_*`, etc. La Fase 6 existe precisamente para limpiarlas. Si se omite la Fase 6, Odoo fallará con `IntegrityError`.

```sql
-- Primero los datos de módulo (dependencias de otros registros)
DELETE FROM ir_model_data
WHERE module LIKE '{MODULE_PREFIX}%'
  AND module NOT IN ({MODULOS_CONSERVAR});

-- Luego el registro del módulo en sí
DELETE FROM ir_module_module
WHERE name LIKE '{MODULE_PREFIX}%'
  AND name NOT IN ({MODULOS_CONSERVAR});
```

---

### Fase 5 — Limpieza de Dependencias

**Objetivo:** Eliminar dependencias hacia módulos que ya no existen.

```sql
DELETE FROM ir_module_module_dependency
WHERE name LIKE '{MODULE_PREFIX}%'
  AND name NOT IN ({MODULOS_CONSERVAR});
```

---

### Fase 6 — Corregir FK Huérfanas

**Objetivo:** Eliminar registros en tablas relacionales que referencian filas ya inexistentes. Este script recorre todas las FK del sistema y borra los registros huérfanos del lado referenciante.

> **NOTA SOBRE DATA NATIVA:** Este script **NUNCA** elimina registros nativos (ej. `account.move`) que tengan referencias válidas. Solo elimina filas donde el registro referenciado ya no existe. La data nativa se conserva íntegra.

**Ejecutar al menos 2 veces** (la primera pasada puede exponer nuevos huérfanos en cascada):

```sql
DO $$ DECLARE fk RECORD; BEGIN
    FOR fk IN SELECT conname, conrelid::regclass AS src, confrelid::regclass AS ref, conkey, confkey
        FROM pg_constraint WHERE contype = 'f' AND confrelid::regclass::text NOT LIKE 'ir_%'
    LOOP
        EXECUTE format(
            'DELETE FROM %I t WHERE t.%I IS NOT NULL AND NOT EXISTS (SELECT 1 FROM %I r WHERE r.%I = t.%I)',
            fk.src,
            (SELECT a.attname FROM pg_attribute a WHERE a.attrelid = fk.src AND a.attnum = fk.conkey[1]),
            fk.ref,
            (SELECT a.attname FROM pg_attribute a WHERE a.attrelid = fk.ref AND a.attnum = fk.confkey[1]),
            (SELECT a.attname FROM pg_attribute a WHERE a.attrelid = fk.src AND a.attnum = fk.conkey[1])
        );
    END LOOP;
END; $$;
```

---

### Fase 7 — Limpieza de otros registros huérfanos

La purga de `ir_model_data` deja registros huérfanos en varias tablas que no tienen FK formal pero sí dependencia lógica. Limpiarlas evita errores al montar la BD.

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

**7d. Acciones URL y actions de servidor huérfanas**

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

**7e. Menús huérfanos (apuntan a acciones o modelos eliminados)** — solo desactivar, no borrar:

```sql
UPDATE ir_ui_menu
SET active = false
WHERE (action IS NOT NULL AND action != '' AND action LIKE 'ir.act%')
  AND NOT EXISTS (
      SELECT 1 FROM ir_act_window a WHERE a.id = ir_ui_menu.action::int
      UNION ALL
      SELECT 1 FROM ir_act_url a WHERE a.id = ir_ui_menu.action::int
      UNION ALL
      SELECT 1 FROM ir_act_client a WHERE a.id = ir_ui_menu.action::int
      UNION ALL
      SELECT 1 FROM ir_act_server a WHERE a.id = ir_ui_menu.action::int
  );
```

---

### Fase 8 — Sincronización

**Objetivo:** Estabilizar el sistema para que Odoo reconozca los cambios.

```bash
odoo -d <DB_NAME> -u base --workers=0 --max-cron-threads=0 --stop-after-init
```

- `--workers=0`: evita deadlocks en proceso de upgrade.
- `--max-cron-threads=0`: no ejecutar crons durante la sincronización.
- `--stop-after-init`: termina Odoo apenas termina el upgrade, no lo deja corriendo.

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
- **Las Fases son secuenciales y dependientes.** Saltarse una fase (especialmente la 6 después de la 4) deja la BD en estado inconsistente.
- **La data nativa (account.move, res.partner, sale.order, etc.) se preserva.** Los scripts están diseñados para solo eliminar metadatos, registros huérfanos y referencias rotas. Nunca se ejecuta un `DELETE` ni `TRUNCATE` sobre tablas de negocio nativas.
- **Excepción:** Si un módulo de la localización creó modelos propios (ej. `binaural_brand`) con datos, esos datos se conservan en la tabla física aunque Odoo ya no los reconozca. Si se desea eliminarlos, hacerlo manualmente con `DROP TABLE IF EXISTS` después de verificar que ninguna tabla nativa tiene FK hacia ellos (Fase 1 ya las anuló).
- Los módulos purgados pueden permanecer en el addons_path sin riesgo; Odoo simplemente los ignorará al no tener entrada en `ir_module_module`.
