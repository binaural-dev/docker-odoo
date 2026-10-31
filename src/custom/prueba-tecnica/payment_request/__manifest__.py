{
    "name": "Solicitudes de Pago",
    "version": "17.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Gestión y aprobación de solicitudes de pago a proveedores",
    "author": "Kenner Cadenas / Binaural",
    "license": "LGPL-3",
    "depends": ["base", "mail", "account"],
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
