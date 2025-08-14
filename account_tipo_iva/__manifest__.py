# -*- coding: utf-8 -*-
{
'name': 'Tipo IVA',
'version': '1.0',
'category': 'Update',
'description': """Módulo  para administracion de tipos de iva
""",
'author': 'Rapidsoft',
'website': 'http://www.rapidsoft.com.py',
# 'depends': ['l10n_py','l10n_py_toponyms','partner_ruc','base','account','account_accountant','stock','account_voucher','purchase_stock','assets_paraguay'],
'depends': ['base','account','paraguay_backoffice'],
'data': [
        'security/ir.model.access.csv',
        'data/tipos_iva.xml',
        'views/invoice_view.xml',
        'views/view_tipo_iva.xml',
],
        'installable': True,
        'auto_install': False,
        'application': True,
        'license': 'LGPL-3',

}
