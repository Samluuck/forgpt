# -*- coding: utf-8 -*-
{
    'name': 'Paraguay - Formulario 500 IRE',
    'version': '15.0.1.0.0',
    'category': 'Accounting/Localizations/Reporting',
    'summary': 'Generación del Formulario 500 - Impuesto a la Renta Empresarial (IRE) - Régimen General',
    'description': """
Paraguay - Formulario 500 IRE
==============================

Módulo para generar el Formulario 500 del SET Paraguay:

* Formulario 500 - Declaración Jurada del IRE Régimen General
* Exportación en formato Excel
* Cálculo automático desde datos contables
* Compatible con la normativa paraguaya del SET
    """,
    'author': 'Regier Custom',
    'depends': ['account', 'l10n_py'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/f500_wizard_views.xml',
        'views/menuitem.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
