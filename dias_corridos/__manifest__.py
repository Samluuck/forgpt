{
    'name': 'HR Días Corridos',
    'version': '1.0',
    'summary': 'Agrega un campo de días corridos al tipo de ausencia',
    'description': 'Este módulo sirve para determinar si el tipo de ausencia debe contarse como días corridos.',
    'category': 'Human Resources',
    'author': 'SATI',
    'depends': ['hr_holidays', 'hr_payroll'],
    'data': [
        'views/hr_leave_type.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}