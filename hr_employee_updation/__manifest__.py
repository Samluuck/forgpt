{
    'name': 'Custodia RRHH Empleado',
    'version': '15.0.1.1.0',
    'summary': """""",
    'description': '',
    'category': '',
    'live_test_url': '',
    'author': '',
    'company': '',
    'website': "",
    'depends': ['base', 'hr', 'mail', 'hr_gamification', 'hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/hr_notification.xml',
        'views/contract_days_view.xml',
        'views/updation_config.xml',
        'views/hr_employee_view.xml',
    ],
    'images': [''],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
