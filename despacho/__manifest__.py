# -*- coding: utf-8 -*-
{
    'name': "Despachos",

    'summary': """
        Módulo para la gestión de despachos aduaneros
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Bellbird",
    'website': "https://bellbird.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Despachos',
    'version': '13.0.0.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_expense'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/views.xml',
        'views/despachos.xml',
        'views/despachos_script.xml',
        'views/administracion.xml',
        'views/partner.xml',
        'reports/report.xml',
        'reports/report_despacho.xml',
        'reports/html_container_custom.xml',
        'reports/report_print_ot_web_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
