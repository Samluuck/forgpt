# -*- coding: utf-8 -*-
{
    'name': 'Informe de Rendimiento',
    'version': '15.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Reporte de rendimiento de proyectos basado en horas trabajadas',
    'description': """
        Informe de Rendimiento de Proyectos
        Este módulo permite generar reportes de rendimiento de proyectos
        mostrando los costos de horas trabajadas por empleado en cada proyecto.

        Características:
        * Filtros por rango de fechas
        * Selección de empleados específicos o todos
        * Filtro por proyectos con/sin horas cargadas
        * Exportación a Excel con estructura personalizada
    """,
    'author': 'Regier',
    'website': 'https://www.regier.com.py',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_timesheet',
        'project',
    ],
    'data': [
        'wizard/informe_rendimiento_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
