{
    "name": "Inspecciones de vehículos",
    "summary": "Checklist de inspección para los vehículos de la flota",
    "version": "19.0.2.0.0",
    "category": "Human Resources/Fleet",
    "author": "Binaural",
    "license": "LGPL-3",
    "depends": ["fleet", "mail"],
    "data": [
        "data/fleet_inspection_item_data.xml",
        "data/fleet_inspection_vehicle_type_data.xml",
        "data/ir_cron_data.xml",
        "data/ir_sequence_data.xml",
        "security/fleet_inspection_security.xml",
        "security/ir.model.access.csv",
        "views/fleet_inspection_item_views.xml",
        "views/fleet_inspection_vehicle_type_views.xml",
        "views/fleet_inspection_views.xml",
        "views/fleet_inspection_menus.xml",
        "report/fleet_inspection_report.xml"
    ],
    "installable": True,
    "application": False,
}