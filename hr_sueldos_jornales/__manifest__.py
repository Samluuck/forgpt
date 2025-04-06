{
    'name': "Sueldos y Jornales",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Genera informe de Sueldos y Jornales',
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
    'depends': ['base', 'hr', 'report_xlsx','hr_wizard_nomina','hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/hr_payroll_config_report.xml',
        'wizard/hr_sueldos_jornales_wizard_view.xml',
        'views/hr_salary_rule.xml',
        'views/hr_entry_type_form_inh.xml',

    ],
    # only loaded in demonstration mode
    'demo': ['demo/demo.xml', ],
}
