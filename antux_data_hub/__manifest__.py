{
    'name': 'Antux Data Hub',
    'summary': 'Centro unificado para la carga, procesamiento y normalización de planillas de clientes.',
    'version': '15.0.1.0.0',
    'description': """
        Antux Data Hub es un módulo diseñado para centralizar la importación y transformación de 
        planillas provenientes de diversos clientes. 

        Funcionalidades principales:
        - Carga de archivos (XLSX/CSV) enviados por clientes.
        - Validación automática de estructura y contenido.
        - Normalización de datos según el formato estándar definido por Antux.
        - Generación de planillas procesadas listas para descarga.
        - Registro histórico de importaciones, errores y estados de procesamiento.
    """,
    
    'author': 'antux',
    'company': 'antux',
    'maintainer': 'antux',
    'website': 'https://antux.com.py/',
    
    'category': 'Tools',
    'license': 'OPL-1',

    'depends': ['base', 'mail'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv', 
        'views/antux_datahub_period_views.xml',
        'views/antux_datahub_batch_views.xml',
        'views/antux_datahub_mapping_views.xml',
        'views/antux_datahub_manual_views.xml',
        'wizard/antux_datahub_import_wizard_views.xml',
        'wizard/antux_datahub_empleados_report_wizard_views.xml',
        'wizard/antux_datahub_ips_report_wizard_views.xml',
        'wizard/antux_datahub_sueldos_jornales_report_wizard_views.xml',
        'wizard/antux_datahub_vacaciones_report_wizard_views.xml',
        'wizard/antux_datahub_resumen_report_wizard_views.xml',
        'wizard/antux_datahub_salary_receipt_wizard_views.xml',
        'reports/salary_receipt_report.xml',
        'views/antux_datahub_menu.xml',
        'data/antux_datahub_mapping_data.xml',
    ],




    'installable': True,
    'auto_install': False,
    'application': True,
}
