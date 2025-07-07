# -*- coding: utf-8 -*-
{
    'name': 'Preventas',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Módulo para la gestión de preventas integrado con CRM y Ventas',
    'description': """
    Este módulo proporciona funcionalidades para la gestión de proyectos de preventas, integrado con los procesos de CRM y Ventas.
    """,
    'author': 'SATI',
    'website': 'http://www.sati.com.py',
    'depends': ['base', 'crm', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/presale_order_views.xml',
        'views/presale_template_views.xml',
        'views/crm_lead_view.xml',
        'views/product_product_views.xml',
        'views/sale_order_views.xml',
        'views/presale_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}