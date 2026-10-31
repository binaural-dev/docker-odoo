{
    "name": "Préstamos de Equipos y Laptops",
    "version": "17.0.1.0.0",
    "category": "Operations/Equipment",
    "summary": "Gestión, registro y control de préstamos de laptops con control de concurrencia y vencimientos",
    "author": "Kenner Cadenas / Binaural",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/equipment_loan_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/equipment_laptop_views.xml",
        "views/equipment_loan_views.xml",
        "views/equipment_loan_menus.xml",
    ],
    "installable": True,
    "application": True,
}

