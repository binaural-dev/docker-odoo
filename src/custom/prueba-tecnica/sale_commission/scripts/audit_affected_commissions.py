#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de auditoría de solo lectura para el incidente T-200 (sale_commission).

Objetivo:
Identificar pedidos de venta confirmados donde las líneas pudieron haber recibido
una comisión incorrecta debido a la confirmación ejecutada por un usuario distinto
al vendedor del pedido (ej. Gerente de Ventas), aprovechando el bug de `self.env.user.commission_percent`.

Modo de uso:
python audit_affected_commissions.py -c /path/to/odoo.conf -d nombre_bd
o mediante Odoo shell:
./odoo-bin shell -c odoo.conf -d nombre_bd < audit_affected_commissions.py
"""

import sys


def audit_orders(env):
    print("=" * 80)
    print(" AUDITORÍA DE PEDIDOS AFECTADOS - INCIDENTE T-200 (SOLO LECTURA)")
    print("=" * 80)

    SaleOrder = env["sale.order"]
    CommissionRule = env["sale.commission.rule"]

    # Buscar pedidos de venta confirmados (state in ['sale', 'done'])
    orders = SaleOrder.search([("state", "in", ("sale", "done"))], order="date_order desc")

    affected_lines_count = 0
    affected_orders = set()

    for order in orders:
        salesman = order.user_id
        if not salesman:
            continue

        order_has_issue = False

        for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
            # 1. Calcular cuál debió ser la regla aplicable
            rules = CommissionRule.search([
                ("categ_id", "parent_of", line.product_id.categ_id.id),
                ("company_id", "in", [False, line.company_id.id]),
            ])

            if rules:
                expected_percent = rules.sorted(lambda r: len(r.categ_id.parent_path or ""), reverse=True)[0].percent
                rule_source = "Regla de Categoría"
            else:
                expected_percent = salesman.commission_percent
                rule_source = f"Porcentaje Vendedor ({salesman.name})"

            actual_percent = line.commission_percent

            # Si la comisión grabada difiere de la esperada
            if abs(actual_percent - expected_percent) > 0.001:
                if not order_has_issue:
                    print(f"\n[!] Pedido: {order.name} | Fecha: {order.date_order} | Vendedor Asignado: {salesman.name}")
                    order_has_issue = True
                    affected_orders.add(order.id)

                affected_lines_count += 1
                expected_amount = line.price_subtotal * expected_percent / 100.0
                diff = expected_amount - line.commission_amount

                print(
                    f"    Línea #{line.id} - Producto: {line.product_id.display_name[:35]:<35} | "
                    f"Subtotal: {line.price_subtotal:10.2f} {order.currency_id.symbol}\n"
                    f"        Comisión Actual : {actual_percent:5.2f}% ({line.commission_amount:8.2f} {order.currency_id.symbol})\n"
                    f"        Comisión Debida : {expected_percent:5.2f}% ({expected_amount:8.2f} {order.currency_id.symbol}) [{rule_source}]\n"
                    f"        Diferencia      : {diff:+8.2f} {order.currency_id.symbol}"
                )

    print("\n" + "=" * 80)
    print(f" RESUMEN DE AUDITORÍA:")
    print(f" Total pedidos afectados encontrados : {len(affected_orders)}")
    print(f" Total líneas afectadas encontradas   : {affected_lines_count}")
    print("=" * 80)
    print(" NOTA: Este script no realizó ninguna modificación en la base de datos.")
    print("=" * 80)


if "env" in locals():
    # Ejecutado dentro de odoo shell
    audit_orders(env)
elif __name__ == "__main__":
    # Ejecutado como script independiente con odoo importado
    try:
        import odoo
        from odoo.tools import config
        config.parse_config(sys.argv[1:])
        registry = odoo.registry(config["db_name"])
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            audit_orders(env)
    except Exception as e:
        print(f"Ejecute este script usando 'odoo-bin shell -c <conf> -d <db> < audit_affected_commissions.py': {e}")

