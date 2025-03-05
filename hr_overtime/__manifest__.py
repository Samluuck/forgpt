# -*- coding: utf-8 -*-
{
    'name': 'Control de solicitud de horas extras',
    'version': '15.0.1.0.0',
    'summary': 'Control de horas extras',
    'description': """
        Helps you to manage Employee Overtime.
        """,
    'category': 'Generic Modules/Human Resources',
    'license': 'LGPL-3',  # Asegúrate de que esta línea esté presente
    'author': "SATI",
    'company': 'SATI',
    'maintainer': 'SATI',
    'website': "sati.com.py",
    'depends': [
        'hr', 'hr_contract', 'hr_attendance', 'hr_holidays', 'project', 'hr_payroll',
    ],
    'external_dependencies': {
        'python': ['pandas'],
    },
    'data': [
        'data/e_data.xml',
        'views/e_overtime_request_view.xml',
        'views/e_overtime_type.xml',
        'views/e_hr_contract.xml',
        'data/recompute_salary.xml',
        'views/e_hr_payslip.xml',
        'security/ir.model.access.csv',
    ],

    'images': ['static/description/overtime_icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
