# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) BrowseInfo (http://browseinfo.in)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'RG90',
    'category': 'Report',
    'description': """
This is the base module to manage the reports for Paraguay.
=====================================================================""",
    'author': 'Sati',
    'website': 'http://www.sati.com.py/',
    'depends': ['base','paraguay_backoffice','partner_ruc','account_voucher','account_payment_py'],
    
    'data': [
        'security/ir.model.access.csv',
        'data/tipo_identificacion.xml',
        'data/tipo_comprobante.xml',
        'views/invoice_view.xml',
        'views/partner_view.xml',
        'views/books_view.xml',
        'views/account_voucher.xml',
        # 'views/account_payment.xml',
        'views/account_voucher_sale.xml',
            # 'reports/revolution_table_report.xml'
    ],
    'demo': [],
    'installable': True,
    'license': 'LGPL-3',
}
