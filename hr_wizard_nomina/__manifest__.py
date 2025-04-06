{
    'name': "Archivo txt",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Generar archivo TXT',
    'description': """
        Long description of module's purpose
    """,
    'author': "SATI",
    'website': 'https://sati.com.py/',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'installable': True,
    'auto_install': False,
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_payroll','report_xlsx','rrhh_basics'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_payroll_txt_wizard.xml',
        'views/views.xml'


    ],
    # only loaded in demonstration mode
    'license': 'AGPL-3',
    'demo': ['demo/demo.xml', ],
}
