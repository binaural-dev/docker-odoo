{
    "name": "Critic Stock Warning",
    "version": "18.0.0.1",
    "author": "Victor Maldonado",
    "category": '',
    "depends": ["base", "product", "mail", "stock"],
    "data":[
        # Security
        "security/stock_control_groups.xml",
        # Templates
        "data/stock_notification_templates.xml",
        # Views
        "views/product_template_view.xml",
        "views/ir_menu_views.xml"
    ],
    "installable": True,
    "application": False,
}