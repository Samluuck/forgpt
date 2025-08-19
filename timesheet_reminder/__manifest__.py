{
    'name': 'Timesheet Reminder',
    'version': '15.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Recordatorio diario para cargar horas en timesheet',
    'description': """
        Módulo que envía recordatorios diarios automáticos a los usuarios
        para que carguen sus horas en el timesheet.
    """,
    'author': 'Tu Empresa',
    'depends': ['base', 'mail', 'hr_timesheet'],
    'data': [
        'data/timesheet_reminder_group.xml',
        'data/timesheet_reminder_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
