{
    'name': "Generar archivo para pago de salarios CONTINENTAL",
    'category': 'Human Resources',
    'version': '1.0',
    'summary': 'Generar archivo para banco',
    'description': """
        Modulo para la creacion del archivo banco
    """,
    'author': "SATI",
    'website': 'https://sati.com.py/',



    'installable': True,
    'auto_install': False,
    'application': True,

    'depends': ['base', 'hr', 'hr_payroll','report_xlsx','hr_documenta'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/hr_payroll_wizard.xml',
    ],
    'demo': ['demo/demo.xml', ],
}
