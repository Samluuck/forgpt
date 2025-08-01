# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################


class account_journal(models.Model):
    _inherit = 'account.journal'

    checkbook_ids = fields.One2many(
        'account.checkbook',
        'journal_id',string="Chequeras"
        )



    def _get_payment_subtype(self):
        selection = super(account_journal, self)._get_payment_subtype()
        selection.append(('issue_check', _('Cheques Propios')))
        selection.append(('third_check', _('Cheques de Terceros')))
        # same functionality as checks, no need to have both for now
        # selection.append(('promissory', _('Promissory Note')))
        return selection
