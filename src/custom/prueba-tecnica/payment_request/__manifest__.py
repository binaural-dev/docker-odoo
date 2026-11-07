{
    "name": "Solicitudes de Pago con Aprobación",
    "summary": "Gestión de solicitudes de pago a proveedores con flujo de aprobación y control de tesorería",
    "version": "17.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Binaural",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/payment_request_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/payment_request_views.xml",
        "views/payment_request_menus.xml",
    ],
    "installable": True,
    "application": True,
}

