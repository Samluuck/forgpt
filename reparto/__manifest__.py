# -*- coding: utf-8 -*-
{
    'name': "reparto",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SATI",
    'website': "http://www.sati.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','fleet','paraguay_backoffice'],

    # always loaded
    'data': [
        'security/grupos.xml',
        'security/reglas.xml',
        'security/ir.model.access.csv',
        'views/delivery_order.xml',
        'views/invoice_views.xml',
        'views/partner_views.xml',
        # 'views/sale_views.xml',
        'views/stock_views.xml',
        'sequence/reparto_sequence.xml',
        'wizard/asignar_reparto_camino.xml',
        'wizard/asignar_reparto_entregado.xml',
        'views/menu.xml',
        'reports/acuse_reparto.xml',
    ],

}
