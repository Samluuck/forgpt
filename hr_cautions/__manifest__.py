{
    'name': "Amonestaciones",

    'summary': """
        Administration of employee reprimands
        """,

    'description': """


    """,

    'author': "SATI",
    'website': "http://www.sati.com.py",
    'license': 'AGPL-3',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'App',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base' ,'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/hr_caution_sequence.xml',
        'views/hr_cautions_view.xml',
        'views/hr_employee_view.xml',
        'reports/boton_imprimir.xml',
        'reports/reporte_amonestaciones.xml',


    ],

}