# -*- coding: utf-8 -*-
{
    'name': "reparto_yasy",

    'description': """
        Modulo de reparto personalizado para YASY PORA S.A
    """,

    'author': "SATI",
    'website': "http://www.sati.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','fleet','paraguay_backoffice','product', 'reparto'],

    'data': [
        'views/delivery_order_inherit_view.xml',
        'views/product_template_extended.xml',
        'reports/deposito_facturas_template.xml',
        'reports/deposito_facturas_report.xml',
        'reports/informe_carga.xml',
        # 'wizard/deposito_facturas_wizard.xml',
    ],

}
