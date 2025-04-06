{
    'name': "Empleados y Obreros",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Genera informe de Empleados y Obreros',
    'description': """
        Reporte de empleados y obreros 
    """,
    'author': "SATI",
    'website': 'https://sati.com.py/',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'report_xlsx'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/hr_payroll_config_report.xml',
        'wizard/hr_empleados_obreros_wizard_view.xml',
        'views/res_country.xml'
    ],
    # only loaded in demonstration mode
    'demo': ['demo/demo.xml', ],
}
