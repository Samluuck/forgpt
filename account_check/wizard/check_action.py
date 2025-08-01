# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################
from odoo.exceptions import Warning
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


class account_check_action(models.TransientModel):
    _name = 'account.check.action'

    
    def _get_company_id(self):
        active_ids = self._context.get('active_ids', [])
        checks = self.env['account.check'].browse(active_ids)
        company_ids = [x.company_id.id for x in checks]
        if len(set(company_ids)) > 1:
            raise Warning(_('All checks must be from the same company!'))
        return self.env['res.company'].search(
            [('id', 'in', company_ids)], limit=1)

    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        domain="[('company_id','=',company_id), "
        "('type', 'in', ['cash', 'bank', 'general']), "
        "('payment_subtype', 'not in', ['issue_check', 'third_check'])]"
        )
    account_id = fields.Many2one(
        'account.account',
        'Account',

        )
    date = fields.Date(
        'Date', required=True, default=fields.Date.context_today
        )
    action_type = fields.Char(
        'Action type passed on the context'
        )
    check_type = fields.Char(
        'Check type passed on the context'
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=_get_company_id
        )

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.account_id = self.journal_id.default_account_id.id


    def validate_action(self, action_type, check):
        # state controls
        if action_type == 'deposit':
            if check.type == 'third_check':
                if check.state != 'holding':
                    raise Warning(
                        _('The selected checks must be in holding state.'))
            else:   # issue
                raise Warning(_('You can not deposit a Issue Check.'))
        elif action_type == 'debit':

            if check.type == 'issue_check':
                if check.state != 'signed':
                    raise Warning(
                        _('The selected checks must be in signed state.'))
            else:   # third
                raise Warning(_('You can not debit a Third Check.'))
        elif action_type == 'return':
            if check.type == 'third_check':
                if check.state != 'holding':
                    raise Warning(
                        _('The selected checks must be in holding state.'))
            # TODO implement return issue checs and return handed third checks
            else:   # issue
                raise Warning(_('You can not return a Issue Check.'))
        elif action_type == 'conciliar':
            if check.state != 'handed':
                raise Warning(_('No se pueden conciliar cheques cuyo estado no sea el de Entregado'))
            else:
                check.state = 'conciliado'
        return True


    def action_confirm(self):
        self.ensure_one()

        # used to get correct ir properties
        self = self.with_context(
            company_id=self.company_id.id,
            force_company=self.company_id.id,
            )

        for check in self.env['account.check'].browse(
                self._context.get('active_ids', [])):

            if self.action_type == 'conciliar':
                # signal = 'handed_conciliado'
                # bank_statement_vals = {
                #     'name': 'Cheque nro. ' + check.name,
                #     'journal_id': check.checkbook_id.debit_journal_id.id,
                #     'date': check.debit_account_move_id.date,
                # }
                # bank_statement = self.env['account.bank.statement'].create(bank_statement_vals)
                # bank_statement_lines_vals = {
                #     'name': 'Cheque nro. ' + check.name,
                #     'statement_id': bank_statement.id,
                #     'partner_id': check.destiny_partner_id.id,
                #     'amount': -check.amount,
                #     'date': check.debit_account_move_id.date,
                #     'ref': check.debit_account_move_id.ref,
                # }
                # bank_statement_lines = self.env['account.bank.statement.line'].create(bank_statement_lines_vals)
                check.state = 'conciliado'
            else:

                vals = self.get_vals(self.action_type, check, self.date)

                # extraemos los vals
                move_vals = vals.get('move_vals', {})
                debit_line_vals = vals.get('debit_line_vals', {})
                credit_line_vals = vals.get('credit_line_vals', {})
                check_move_field = vals.get('check_move_field')
                signal = vals.get('signal')

                move = self.env['account.move'].with_context(check_move_validity=False).create(move_vals)
                debit_line_vals['move_id'] = move.id
                credit_line_vals['move_id'] = move.id

                move.line_ids.with_context(check_move_validity=False).create(debit_line_vals)
                move.line_ids.with_context(check_move_validity=False).create(credit_line_vals)

                check.write({check_move_field: move.id, 'state':'conciliado'})

                # check.signal_workflow(signal)
                move.post()

        return True
    
    def get_vals(self, action_type, check, date):

        vou_journal = check.voucher_id.journal_id
        if not vou_journal:
            vou_journal = check.checkbook_id.journal_id
        # TODO improove how we get vals, get them in other functions
        if self.action_type == 'deposit':
            ref = _('Deposit Check Nr. ')
            check_move_field = 'deposit_account_move_id'
            journal = self.journal_id
            debit_account_id = self.account_id.id
            partner = check.source_partner_id.id,
            credit_account_id = vou_journal.default_account_id.id
            signal = 'holding_deposited'
        elif self.action_type == 'debit':
            ref = _('Debit Check Nr. ')
            check_move_field = 'debit_account_move_id'
            journal = check.checkbook_id.debit_journal_id
            partner = check.destiny_partner_id.id
            credit_account_id = journal.default_account_id.id
            debit_account_id = vou_journal.default_account_id.id
            signal = 'signed_handed'
        elif self.action_type == 'return':
            ref = _('Return Check Nr. ')
            check_move_field = 'return_account_move_id'
            journal = vou_journal
            debit_account_id = (
                check.source_partner_id.property_account_receivable.id)
            partner = check.source_partner_id.id,
            credit_account_id = vou_journal.default_account_id.id
            signal = 'holding_returned'
       # seq_id = self.pool.get('ir.sequence').search(cr, uid, ['TESTSEQ'])
        #name = journal.sequence_id.with_context(self.env['ir.sequence']).next()
        #sequence_obj = self.pool.get('ir.sequence')
        #name = sequence_obj.next_by_id(journal.sequence_id.id)
#         seq_id=self.env['ir.sequence'].search([('id', '=', journal.sequence_id.id)])
        name = 'Cobro Cheq. Dif.' + str(check.name)
        ref += check.name
        move_vals = {
            'name': name,
            'journal_id': journal.id,
            'date': self.date,
            'ref':  ref,
        }
        monto = 0
        if self.env.company.currency_id != check.currency_id:
            tasa = self.env['res.currency.rate'].search([('currency_id','=',check.currency_id.id),('name','=',self.date)])
            if len(tasa) > 0:
                monto = tasa[0].set_venta * check.amount
            else:
                raise ValidationError('Favor actualizar tasa')
        else:
            monto = check.amount
        debit_line_vals = {
            'name': name,
            'account_id': debit_account_id,
            'partner_id': partner,
            'debit': monto,
            'credit' : 0,
            'currency_id': check.currency_id.id,
            'amount_currency' : check.amount,
            'ref': ref,
        }
        #raise exceptions.ValidationError(debit_line_vals['ref'])
        credit_line_vals = {
            'name': name,
            'account_id': credit_account_id,
            'partner_id': partner,
            'debit' : 0,
            'credit': monto,
            'currency_id': check.currency_id.id,
            'amount_currency': -check.amount,
            'ref': ref,
        }
        #raise exceptions.ValidationError(credit_line_vals['amount_currency'])
        return {
            'move_vals': move_vals,
            'debit_line_vals': debit_line_vals,
            'credit_line_vals': credit_line_vals,
            'check_move_field': check_move_field,
            'signal': signal,
            }

