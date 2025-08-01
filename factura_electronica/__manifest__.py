{
    'name': "factura_electronica",

    'summary': """
        Modulo de Factura Electronica Paraguay""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SATI",
    'website': "http://www.sati.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','paraguay_backoffice','web_domain_field'],

    # always loaded
    'data': [
        'security/grupo_facturacion_electronica.xml',
        'security/ir.model.access.csv',
        'views/invoice.xml',
        'views/timbrado.xml',
        'views/company.xml',
        'views/partner.xml',
        'views/journal.xml',
        'views/payment.xml',
        'views/checkbook.xml',
        'views/product_template.xml',
        'views/product_product.xml',
        'views/product_uom.xml',
        'views/account_tax.xml',
        'views/eventos_dte.xml',
        'views/consulta_dte.xml',
        'wizard/certificate_pass_view.xml',
        'views/firma_digital.xml',
        'views/res_country.xml',
        'views/envio_lotes.xml',
        'views/msjes_resultado.xml',
        'reports/config.xml',
        'reports/factura_report.xml',
        'reports/factura_report_2.xml',
        'wizard/consulta_ruc.xml',
        'sequence/sequence_fe.xml',
        'views/menus.xml',
    ],

}
# -*- coding: utf-8 -*-
