# -*- coding: utf-8 -*-
{
    'name': "accounting_reports_paraguay",
    'version': '1.0',


    'description': """
        Modulo a para generación de informes contables conforme a normativas de Paraguay (con formato de rúbrica):
            * Libro diario
            * Libro mayor
            * Libro Inventario
            * Reportes Res. 49:
                - Balance Gral.
                - Estado de Resultados.
                - Flujo de Efectivo.
                - Cuadro de Revalúo.
                - Nota de presentación de los estados contables.
                - Estado de cambios del Patrimonio Neto
                
                
        Para la utilizacion del Estado de Resultado, en las cuentas contables se les debe asignar un grupo en el formulario de Cuenta Contable.
    """,

    'author': "SATI",
    'name': 'Reportes Contables Paraguay',
    'category': 'Application',
    'website': 'https://www.sati.com.py',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','paraguay_backoffice','account_tipo_iva','l10n_py'],

    # always loaded
    'data': [
        # 'data/account_group.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'reports/config_accounting_reports_paraguay.xml',
        'reports/libro_diario_paraguay_report.xml',
        'reports/libro_mayor_paraguay_report.xml',
        'reports/libro_iva_paraguay_report.xml',
        'reports/balance_report.xml',
        'reports/resultados_report.xml',
        'reports/estado_patrimonio_report.xml',
        'reports/flujo_efectivo_report.xml',
        'reports/notas_eeff_report.xml',
        'reports/cuadro_revaluo_report.xml',
        'wizard/wizard_libro_diario.xml',
        'views/account_accout.xml',
        'wizard/wizard_libro_mayor.xml',
        'wizard/wizard_libro_iva.xml',
        'wizard/wizard_balance_gral.xml',
        'wizard/wizard_resultados_gral.xml',
        'wizard/wizard_notas_eeff.xml',
        'wizard/cierre_asiento_wizard.xml',
        'wizard/wizard_cuadro_revaluo.xml',
        'wizard/wizard_hechauka_eerr_balance.xml',
        'views/anexos_view.xml',
        'wizard/wizard_estado_patrimonio.xml',
        'wizard/wizard_flujo_efectivo.xml',
        'views/account_move_view.xml',
        'views/company.xml',
        'views/anexo5_view.xml',
        'views/action_extend.xml',
        'views/menu_view.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}