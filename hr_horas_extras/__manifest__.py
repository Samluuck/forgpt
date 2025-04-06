{
    'name': 'Horas Extras Empleado',
    'version': '15.0.1.0.0',
    'summary': """Este modulo calcula las horas extras trabajadas por el empleado""",
    'description': """Este modulo calcula las horas extras trabajadas por el empleado""",
    'author': "SATI",
    'company': 'SATI',
    'website': 'https://sati.com.py/',
    'maintainer': '',
    'category': 'Human Resources',
    'depends': ['hr_attendance', 'hr_contract','hr_payroll','hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_inh.xml',
        'views/hr_payslip_view.xml',
        'views/res_config_settings.xml',
        'views/hr_attendance_view.xml',

        'wizard/employee_attendance_report_views.xml',

    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
