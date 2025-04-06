{
    'name': "Vacaciones Paraguay",

    'summary': """
        Cálculo automático de vacaciones y asignación de dias disponibles para cada empleado.
        """,

    'description': """
    Este módulo instala una acción planificada (CRON) que se ejecuta una vez al día,
    verificando la cantidad de días disponibles de vacaciones y asignando de manera automática
    al empleado.

    """,

    'author': "SATI",
    'website': "http://www.sati.com.py",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'App',
    'version': '0.1',
    'license': 'AGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_holidays', 'hr_contract'],

    # always loaded
    'data': [
        'data/vacaciones_cron_data.xml',
        'views/hr_employee_view.xml',
        'views/hr_leave_type_view.xml',
    ],

}
# -*- coding: utf-8 -*-
