{
    'name': 'HR Balance Leave Report',
    'version': '',
    'category': 'Human Resources/Time Off',
    'summary': 'Allocated balance, taken leaves and remaining balance per leave type for each employee',
    'description': 'User Can view Allocated balance, taken leaves and remaining balance per leave type for '
                   'each employee',
    'author': '',
    'company': '',
    'maintainer': '',
    'website': '',
    'depends': ['hr', 'hr_holidays','hr_payroll'],
    'data': [
        'security/balance_report_security.xml',
        'security/ir.model.access.csv',
        'report/leave_balance_report_view.xml',
        'report/hr_payslip_view.xml'

    ],
    'images': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
