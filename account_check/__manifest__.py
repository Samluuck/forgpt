# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    'name': 'Account Check Management',
    'version': '8.0.2.3.1',
    'category': 'Accounting',
    'sequence': 14,
    'summary': 'Accounting, Payment, Check, Third, Issue',
    'description': """
Account Check Management
========================
    """,
    'author':  'Rapidsoft en colaboracion con AdHoc',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_journal_payment_subtype',
        'account',
        'paraguay_backoffice',
        'account_voucher'
    ],
    'data': [
        'wizard/check_action_view.xml',
        'wizard/view_check_reject.xml',
        'wizard/change_check_view.xml',
        'views/account_checkbook_view.xml',
        'views/account_view.xml',
        'views/account_voucher_view.xml',
        'views/account_check_view.xml',
        'security/ir.model.access.csv',
        'security/account_check_security.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
