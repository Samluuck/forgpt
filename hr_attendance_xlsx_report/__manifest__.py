{
    'name': "Employee Attendance Xlsx Report",
    'version': '15.0',
    'category': 'Human Resources/Attendances',
    'summary': """Este módulo gestionará el informe de asistencia de los empleados.
                   en xlsx""",
    'description': """Este módulo ayuda a generar el informe de asistencia de
    empleados en formato XLSX""",
    'author': '',
    'company': '',
    'maintainer': '',
    'website': '',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/employee_attendance_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_xlsx_report/static/src/js/action_manager.js',
        ]
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
