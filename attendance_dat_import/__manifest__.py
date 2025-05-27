{
    'name': 'Importar Asistencias .dat',
    'version': '1.0',
    'depends': ['hr_attendance', 'hr'],
    'autor': 'SATI',
    'website': 'www.sati.com.py',
    'category': 'Human Resources/Attendances',
    'description': 'Importa registros de asistencias desde archivos .dat personalizados',
    'data': [
        'security/ir.model.access.csv',
        'wizard/attendance_import_wizard_view.xml',
        'views/hr_attendance_inherit_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
