{
    "name": "Comisiones de vendedores",
    "summary": "Comisión del vendedor por línea de pedido y análisis mensual",
    "version": "1.1.0",
    "category": "Sales/Sales",
    "author": "Binaural",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "security/sale_commission_security.xml",
        "views/res_users_views.xml",
        "views/product_category_views.xml",
        "views/sale_order_views.xml",
        "report/sale_commission_report_views.xml",
    ],
    "installable": True,
}
