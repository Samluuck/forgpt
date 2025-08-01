# -*- coding: utf-8 -*-
{
    'name': "Despachos",

    'summary': """
        Módulo para la gestión de despachos aduaneros
        """,

    'description': """
        Long description of module's purpose
    """,
    'images': ['static/description/icon.png'],
    'author': "",
    'category': 'Inventory/Inventory',
    'version': '17.0.0.1',
    'depends': ['base', 'hr', 'hr_expense', 'contacts'],
    'data': [
        'security/despacho_security.xml',
        'security/ir.model.access.csv',
        'views/res_users_view.xml',
        'views/views.xml',
        'views/despachos.xml',
        'views/administracion.xml',
        'views/partner.xml',
        'reports/report.xml',
        'reports/report_despacho.xml',
        'reports/report_print_ot_web_template.xml',
        'reports/liquidacion_despacho_template.xml',
    ],

    'application': True,
    'license': 'LGPL-3',
}
