{
    "name": "API para tienda en línea",
    "summary": "Endpoints REST para que la tienda en línea consulte productos con stock y cree pedidos de venta",
    "description": "API REST con API keys para la tienda en línea: productos con stock, pedidos y registro de llamadas. Detalle en README.md.",
    "version": "18.0.1.2.0",
    "category": "Sales/Sales",
    "author": "Candido Marcano",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/shop_api_log_views.xml",
        "views/shop_webhook_event_views.xml",
    ],
    "installable": True,
}
