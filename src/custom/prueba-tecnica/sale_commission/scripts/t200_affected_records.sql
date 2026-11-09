-- T-200 · Registros afectados mientras los vendedores no podían confirmar pedidos.
--
-- SOLO LECTURA: todo corre dentro de una transacción READ ONLY y termina en ROLLBACK.
-- Si alguien agregara un INSERT/UPDATE/DELETE, PostgreSQL lo rechaza.
--
-- Parámetro:
--   since  inicio de la ventana en UTC (despliegue de la 1.1.0). 12:00 m. hora de Venezuela = 16:00 UTC.
--
-- Uso:
--   psql -U odoo -d <base> -v since='2026-10-16 16:00:00' -f t200_affected_records.sql
--   (con --csv para obtener la salida en CSV)
--
-- Sección 1: líneas de pedidos confirmados en la ventana cuyo porcentaje no es el que corresponde.
--   La versión 1.1.0 usaba el porcentaje de QUIEN CONFIRMA cuando la categoría no tenía regla;
--   como esa tarde confirmó el gerente, esas líneas pueden tener el porcentaje del gerente.
-- Sección 2: pedidos a los que se les cambió el vendedor en la ventana (por ejemplo, el gerente se
--   asignó el pedido para poder confirmarlo): la comisión quedaría a nombre de quien no corresponde.

\set ON_ERROR_STOP on
\if :{?since}
\else
  \echo 'Falta el parámetro: -v since=''AAAA-MM-DD HH:MM:SS'' (UTC)'
  \quit
\endif

BEGIN TRANSACTION READ ONLY;

\echo '== Sección 1: líneas con porcentaje de comisión incorrecto =='
WITH lines AS (
    SELECT
        o.name                              AS pedido,
        o.date_order                        AS confirmado_utc,
        seller.login                        AS vendedor,
        confirmer.login                     AS confirmado_por,
        l.id                                AS linea_id,
        pt.name ->> 'en_US'                 AS producto,
        pc.complete_name                    AS categoria,
        l.price_subtotal                    AS subtotal,
        l.commission_percent                AS pct_guardado,
        rule.percent                        AS pct_regla,
        COALESCE(rule.percent, seller.commission_percent, 0) AS pct_correcto,
        l.commission_amount                 AS comision_guardada
    FROM sale_order_line l
    JOIN sale_order o            ON o.id = l.order_id
    JOIN res_users seller        ON seller.id = o.user_id
    JOIN product_product pp      ON pp.id = l.product_id
    JOIN product_template pt     ON pt.id = pp.product_tmpl_id
    JOIN product_category pc     ON pc.id = pt.categ_id
    -- La regla más específica (categoría o ancestro), igual que _get_commission_percent().
    LEFT JOIN LATERAL (
        SELECT r.percent
        FROM sale_commission_rule r
        JOIN product_category rc ON rc.id = r.categ_id
        WHERE pc.parent_path LIKE rc.parent_path || '%'
          AND (r.company_id IS NULL OR r.company_id = l.company_id)
        ORDER BY length(rc.parent_path) DESC, r.id
        LIMIT 1
    ) rule ON TRUE
    -- Quién hizo el último cambio de estado del pedido (la confirmación), según el chatter.
    LEFT JOIN LATERAL (
        SELECT m.create_uid
        FROM mail_message m
        JOIN mail_tracking_value t ON t.mail_message_id = m.id
        JOIN ir_model_fields f     ON f.id = t.field_id
        WHERE m.model = 'sale.order' AND m.res_id = o.id
          AND f.model = 'sale.order' AND f.name = 'state'
        ORDER BY m.id DESC
        LIMIT 1
    ) conf ON TRUE
    LEFT JOIN res_users confirmer ON confirmer.id = conf.create_uid
    WHERE o.state = 'sale'
      AND l.display_type IS NULL
      AND o.date_order >= :'since'::timestamp
)
SELECT
    pedido, confirmado_utc, vendedor, confirmado_por, linea_id, producto, categoria, subtotal,
    pct_guardado, pct_correcto, comision_guardada,
    round(subtotal * pct_correcto / 100.0, 2)                        AS comision_correcta,
    round(subtotal * pct_correcto / 100.0, 2) - comision_guardada    AS diferencia,
    CASE
        WHEN pct_regla IS NULL THEN 'sin regla: tomó el % de quien confirmó'
        ELSE 'con regla: la regla cambió después de confirmar (revisar a mano)'
    END                                                              AS motivo
FROM lines
WHERE pct_guardado IS DISTINCT FROM pct_correcto
ORDER BY confirmado_utc, pedido, linea_id;

\echo '== Sección 2: pedidos con cambio de vendedor en la ventana =='
SELECT
    o.name                  AS pedido,
    o.state                 AS estado,
    m.date                  AS cambio_utc,
    changer.login           AS cambiado_por,
    old_u.login             AS vendedor_anterior,
    new_u.login             AS vendedor_nuevo,
    COALESCE(sum(l.commission_amount), 0) AS comision_del_pedido
FROM mail_tracking_value t
JOIN ir_model_fields f   ON f.id = t.field_id AND f.model = 'sale.order' AND f.name = 'user_id'
JOIN mail_message m      ON m.id = t.mail_message_id AND m.model = 'sale.order'
JOIN sale_order o        ON o.id = m.res_id
LEFT JOIN res_users changer ON changer.id = m.create_uid
LEFT JOIN res_users old_u   ON old_u.id = t.old_value_integer
LEFT JOIN res_users new_u   ON new_u.id = t.new_value_integer
LEFT JOIN sale_order_line l ON l.order_id = o.id AND l.display_type IS NULL
WHERE m.date >= :'since'::timestamp
GROUP BY o.name, o.state, m.date, changer.login, old_u.login, new_u.login
ORDER BY m.date, o.name;

ROLLBACK;
