{
    'name': "Generar archivo para pago de salarios ATLAS",

    'summary': """
Generar archivo TXT para pago de salarios ATLAS desde el Lote de Salarios
""",

    'description': """
Generar archivo TXT para pago de salarios ATLAS desde el Lote de Salarios
""",

    'author': "SATI",
    'website': "https://www.sati.com.py",

    'category': 'Human Resources/Payroll',
    'version': '17.0',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_payroll', 'rrhh_payroll_bancos_familiar'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_company.xml',
        'views/res_bank.xml',
        # 'reports/hr_payslip_run_banco_atlas_report.xml',
        'reports/wizard_bancos_atlas_report.xml',
    ],
}