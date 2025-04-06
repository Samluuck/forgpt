{
    'name': "Registro de Vacaciones",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Genera informe de Registro de Vacaciones',
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
    'license': 'AGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/hr_payroll_config_report.xml',

        'wizard/hr_registro_vacaciones_wizard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': ['demo/demo.xml', ],
}
