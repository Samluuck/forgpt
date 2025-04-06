{
    'name': "Resumen General de Empleados",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Genera informe de Empleados ',
    'description': """
        Long description of module's purpose
    """,
    'author': "SATI",
    'website': 'https://sati.com.py/',
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3',
    'depends': ['base', 'hr', 'report_xlsx','hr_holidays','hr_contract_types'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/hr_payroll_config_report.xml',
        'views/hr_employee_inh.xml',
        'wizard/hr_resumen_general_wizard_view.xml',

    ],
    # only loaded in demonstration mode
    'demo': ['demo/demo.xml', ],
}
