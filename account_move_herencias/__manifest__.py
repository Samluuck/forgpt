{
    "name": "Account Move Herencias",
    "version": "15.0.1.0.0",
    "depends": ["account", "paraguay_backoffice", "factura_electronica", "caja_chica"],
    'category': 'accounting',
    'author': 'Regier',
    'website': 'https://odoo.regier.com.py',
    "data": [
        "views/account_move_views.xml",
        "views/server_actions.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
