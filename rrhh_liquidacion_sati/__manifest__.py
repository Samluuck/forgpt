{
    'name': "Liquidación de salarios",

    'summary': """
Módulo para LIQUIDACIÓN DE SALARIOS""",

    'description': """
Módulo para LIQUIDACIÓN DE SALARIOS
""",

    'author': "SATI",
    'website': "https://sati.com.py/",

    'category': 'Human Resources/Payroll',
    'version': '2024.1.15.1',
    'license': 'AGPL-3',
    'depends': ['base','hr_payroll'],

    'data': [

        'views/hr_payslip_structure.xml',
        'views/hr_payslip.xml',
        'views/hr_salary_rule.xml',

    ],
}
