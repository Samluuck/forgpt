# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _,exceptions
import logging
from odoo.exceptions import Warning
_logger = logging.getLogger(__name__)


class account_checkbook(models.Model):

    _name = 'account.checkbook'
    _description = 'Account Checkbook'
    _inherit = ['mail.thread']
#old method
    #
    #def _get_next_check_number(self):
     #   next_number = self.range_from
      #  check_numbers = [
       #     check.number for check in self.issue_check_ids]
        #if check_numbers:
         #   next_number = max(check_numbers) + 1
        #self.next_check_number = next_numbercehque
#new method

    def _get_next_check_number(self):
        cr=self.env.cr.execute('select max(number) from account_check where checkbook_id =%s', (self.id,))
        number = self.env.cr.fetchone()[0]
        if number:
            self.next_check_number = number + 1
        else:
            self.next_check_number = self.range_from



    name = fields.Char(
        'Nombre', size=30, readonly=True, required=True,tracking=True,
        states={'draft': [('readonly', False)]})
    issue_check_subtype = fields.Selection(
        [('deferred', 'Deferred'), ('currents', 'Currents')],
        string='Subtipo',
        readonly=True,
        required=True,
        default='deferred',
        help='The only difference bewteen Deferred and Currents is that when '
        'delivering a Deferred check a Payment Date is Require',
        states={'draft': [('readonly', False)]})
    debit_journal_id = fields.Many2one(
        'account.journal', 'Diario de Debito',
        help='It will be used to make the debit of the check on checks ',
        required=False,tracking=True,
        domain=[('type', '=', 'bank')],
        context={'default_type': 'bank'})
    journal_id = fields.Many2one(
        'account.journal', 'Diario',
        help='Journal where it is going to be used',
        readonly=True, required=True, domain=[('type', '=', 'bank')],
        context={'default_type': 'bank'},
        states={'draft': [('readonly', False)]})
    range_from = fields.Integer(
        'Numero desde:',tracking=True, readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    range_to = fields.Integer(
        'Numero Hasta', tracking=True,readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    next_check_number = fields.Char(
        compute='_get_next_check_number',
        string=_('Proximo Numero'),)
    padding = fields.Integer(
        'Cantidad de Digitos',
        default=8,
        required=True,tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="automatically adds some '0' on the left of the 'Number' to get "
        "the required padding size.")
    company_id = fields.Many2one(
        'res.company',
        related='journal_id.company_id',
        requirde=True, readonly=True,
        string='Company', store=True)
    issue_check_ids = fields.One2many(
        'account.check', 'checkbook_id', string='Issue Checks', readonly=True,)
    state = fields.Selection(
        [('draft', 'Draft'), ('active', 'In Use'), ('used', 'Used')],
        string='State', readonly=True, default='draft', copy=False)
    obra = fields.Many2one('stock.warehouse', string='Centro de costo', change_default=True, tracking=True)

    _order = "name"

    # def _check_numbers(self, cr, uid, ids, context=None):
    #     record = self.browse(cr, uid, ids, context=context)
    #     for data in record:
    #         if (data.range_to <= data.range_from):
    #             return False
    #     return True

    # _constraints = [
    #     (_check_numbers, 'Range to must be greater than range from',
    #      ['range_to', 'range_from']),
    # ]

    #
    @api.constrains('padding')
    @api.onchange('padding')
    def check_padding(self):
        if self.padding > 32:
            raise Warning(
                _('Padding must be lower than 32'))

    #
    @api.constrains('debit_journal_id', 'journal_id')
    def check_journals(self):
        if self.journal_id.company_id != self.debit_journal_id.company_id:
            raise Warning(
                _('Journal And Debit Journal must belong to the same company'))

    #
    def unlink(self):
        if self.state not in ('draft'):
            raise Warning(
                _('You can drop the checkbook(s) only in draft state !'))
        return super(account_checkbook, self).unlink()


    def set_used(self):
        self.write({'state': 'used'})
        return True


    def set_active(self):
        self.write({'state': 'active'})
        return True


    def set_draft(self):
        self.write({'state': 'draft'})
        return True
