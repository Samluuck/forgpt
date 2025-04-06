{
    'name': 'Birthday Notification',
    'version': '15.0.1.0',
    'summary': 'Deseos de cumpleaños para empleados y contactos',
    'description': """
Este módulo envía notificaciones por correo electrónico para deseos de cumpleaños a empleados y contactos.

    bendiciones de cumpleaños
    Tarjeta de cumpleaños
    alegría de cumpleaños
    notificación de cumpleaños
    Saludos de cumpleaños
    mensaje de cumpleaños
    recordatorio de cumpleaños
    Deseos de cumpleaños
    Dicha
    Notificación de correo electrónico
    Ocasión feliz
    Momento
    Día especial
    Deseos
    Tu día
    """,
    'category': 'Tools',
    'license': 'OPL-1',
    'author': 'Kanak Infosystems LLP.',
    'website': 'https://www.kanakinfosystems.com',
    'depends': ['base_setup', 'hr', 'contacts'],
    'images': ['static/description/banner.jpg'],
    'data': [
        'data/knk_mail_data.xml',
        'data/knk_cron_data.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
