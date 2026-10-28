"""Simula en una base de PRUEBAS los datos que dejó el incidente T-200. Nunca en producción.

Reproduce lo que pasó la tarde del despliegue de la 1.1.0: el gerente confirmó pedidos de los
vendedores y, en las líneas sin regla de categoría, la 1.1.0 guardó el porcentaje del gerente.

Uso (base recién creada con sale_commission instalado):
    odoo shell -c <odoo.conf> -d <base> --no-http < t200_seed_incident.py
"""
from odoo.tests.common import new_test_user

admin = env.ref("base.user_admin")
seller_a = new_test_user(env, login="t200_vendedor_a", groups="sales_team.group_sale_salesman", name="Vendedor A")
seller_b = new_test_user(env, login="t200_vendedor_b", groups="sales_team.group_sale_salesman", name="Vendedor B")
manager = new_test_user(env, login="t200_gerente", groups="sales_team.group_sale_manager", name="Gerente")
seller_a.commission_percent = 5.0
seller_b.commission_percent = 3.0
manager.commission_percent = 12.0

partner = env["res.partner"].create({"name": "Cliente T-200"})
categ_services = env["product.category"].create({"name": "Servicios T-200"})
categ_parts = env["product.category"].create({"name": "Repuestos T-200"})
categ_parts.commission_percent = 8.0
service = env["product.product"].create({
    "name": "Servicio T-200", "categ_id": categ_services.id, "list_price": 100.0, "taxes_id": [(5, 0, 0)],
})
part = env["product.product"].create({
    "name": "Repuesto T-200", "categ_id": categ_parts.id, "list_price": 50.0, "taxes_id": [(5, 0, 0)],
})


def make_order(seller, products):
    order = env["sale.order"].with_user(seller).create({
        "partner_id": partner.id,
        "user_id": seller.id,
        "order_line": [(0, 0, {"product_id": p.id, "product_uom_qty": 1}) for p in products],
    })
    return order.with_env(env)


def confirm_as_v110(order, user):
    """Confirma como `user` y deja el porcentaje que habría guardado la 1.1.0 (el de quien confirma)."""
    order.with_user(user).action_confirm()
    rules = env["sale.commission.rule"]
    for line in order.order_line:
        # Con regla de categoría la 1.1.0 calculaba bien; sin regla usaba env.user.
        if not rules.search_count([("categ_id", "parent_of", line.product_id.categ_id.id)]):
            line.commission_percent = user.commission_percent


# Los vendedores crean sus cotizaciones (en la mañana).
o1 = make_order(seller_a, [service])
o2 = make_order(seller_a, [service])
o3 = make_order(seller_b, [part])
o4 = make_order(seller_b, [service, part])
o5 = make_order(seller_a, [service])
make_order(seller_b, [service])  # 6. Cotización sin confirmar: no debe aparecer.
# Un commit por acción, como en producción (cada clic es una petición con su usuario): el chatter
# solo registra cambios de registros guardados antes, y publica el seguimiento con el usuario de
# la transacción.
env.cr.commit()

# 1. El vendedor confirma su propio pedido (después del hotfix): correcto.
o1.with_user(seller_a).action_confirm()
env.cr.commit()
# 2. El gerente confirma el pedido del vendedor A, sin regla: queda con 12 % en vez de 5 %. AFECTADO.
confirm_as_v110(o2, manager)
env.cr.commit()
# 3. El gerente confirma el pedido del vendedor B, con regla de categoría (8 %): correcto.
confirm_as_v110(o3, manager)
env.cr.commit()
# 4. Pedido mixto del vendedor B confirmado por el gerente: la línea de servicio queda en 12 % (AFECTADA),
#    la de repuesto en 8 % (correcta).
confirm_as_v110(o4, manager)
env.cr.commit()
# 5. El gerente se asigna el pedido del vendedor A y lo confirma: la comisión queda a nombre del gerente.
o5.with_user(manager).user_id = manager
confirm_as_v110(o5, manager)

env.cr.commit()
print("Pedidos creados:", ", ".join((o1 | o2 | o3 | o4 | o5).mapped("name")))
print("Esperado sección 1: líneas de servicio de", o2.name, "y", o4.name)
print("Esperado sección 2:", o5.name)
