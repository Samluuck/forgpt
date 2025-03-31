# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Fasluca(<faslu@cybrosys.in>)
#    you can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Manual Bank Reconciliation',
    'version': '17.0.1.0',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'http://www.cybrosys.com',
    'category': 'Accounting',
    'summary': 'Replacing default method by traditional',
    'description': """ Replacing default bank statement reconciliation method by traditional way """,
    'depends': ['account','account_cobros_py'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_line_view.xml',
        'views/account_journal_dashboard_view.xml',
        'wizard/bank_statement_export_by_date_view.xml',
        'wizard/bank_statement_wiz_view.xml',
        'wizard/wizard_book_bank.xml',
        'reports/reports_config.xml',
        # 'reports/bank_reconciliation_reports.xml',
        # 'views/account_account_view.xml',
        'reports/book_bank_report.xml',
        'reports/bank_reconciliation_reports.xml',
        'wizard/bank_statement_import.xml',

    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,

}
