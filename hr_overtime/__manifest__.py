# -*- coding: utf-8 -*-
{
    'name': 'Control de solicitud de horas extras',
    'version': '15.0.1.0.0',
    'summary': 'Control de horas extras',
    'description': """
        Helps you to manage Employee Overtime.
        """,
    'category': 'Generic Modules/Human Resources',
    'license': 'LGPL-3',
    'author': "SATI",
    'company': 'SATI',
    'maintainer': 'SATI',
    'website': "sati.com.py",
    'depends': [
        'hr', 'hr_contract', 'hr_attendance', 'hr_holidays', 'project', 'hr_payroll', 'hr_documenta',
    ],
    'external_dependencies': {
        'python': ['pandas'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/e_data.xml',
        'views/e_hr_employee.xml',
        'views/e_overtime_request_view.xml',
        'views/e_overtime_type.xml',
        'views/e_hr_contract.xml',
        'data/recompute_salary.xml',
        'views/e_hr_payslip.xml'
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
