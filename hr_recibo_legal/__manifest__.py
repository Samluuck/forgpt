{
    'name': "Recibo Salarial ",
    'summary': """
        Recibo Salarial""",
    'description': """
         Modulo para imprimir un recibo de nomina
    """,
     'author': "SATI",
    'website': "https://sati.com.py/",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    'category': 'Human Resources/Employees',
    'version': "15.0.0.0.0",
    'license': 'AGPL-3',
    'support': "support@loyalitsolutions.com",
    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_payroll', 'hr_sueldos_jornales'],
    # always loaded
    'data': [
        'views/templates.xml',
        'views/payslip_print.xml',
        'views/hr_payslib.xml',
        'views/hr_work_entry.xml',
    ],

    'images': ['static/description/banner.png'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
