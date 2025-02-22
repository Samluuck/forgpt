{
    'name': "Generar archivo para pago de salarios ITAU",

    'summary': """
Generar archivo TXT para pago de salarios ITAU desde el Lote de Salarios
""",

    'description': """
Generar archivo TXT para pago de salarios ITAU desde el Lote de Salarios
""",

    'author': "SATI",
    'website': "https://www.sati.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Payroll',
    'version': '2023.12.15.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_company.xml',
        'views/res_bank.xml',
        'reports/hr_payslip_run_banco_itau_report.xml',
        'reports/wizard_bancos_itau_report.xml',
    ],
}
