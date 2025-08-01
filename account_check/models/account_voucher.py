# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _, api
import odoo.addons.decimal_precision as dp
import logging
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class voucher(models.Model):
    _inherit= 'account.voucher'

    payment_journal_id = fields.Many2one('account.journal', string='Metodo de Pago',domain="[('type', 'in', ['cash','retencion','tarjeta_credito','tarjeta_debito','bank'])]")
    type_journal = fields.Selection(related='payment_journal_id.payment_subtype', readonly=True)
    check_id = fields.Many2one('account.check', string="Cheque",tracking=True)
    check_third_id = fields.Many2one('account.check.third', string="Cheque",tracking=True)
    verificar_pago_cheque=fields.Boolean(compute='ver_cheque')
    extranjero = fields.Boolean(compute='verificar_monedas')
    balance_foreign_account = fields.Float(compute='compute_balance')
    balance = fields.Float(compute='compute_balance')

    @api.depends('payment_journal_id')
    def compute_balance(self):
        for rec in self:
            m=0
            if rec.payment_journal_id:
                if rec.payment_journal_id.currency_id and rec.payment_journal_id.currency_id != self.env.company.currency_id:
                    saldos=self.env['account.move.line'].search([('move_id.state','=','posted'),('account_id','=',rec.payment_journal_id.default_account_id.id)])
                    m = sum([m.amount_currency for m in saldos])
                else:
                    saldos=self.env['account.move.line'].search([('move_id.state','=','posted'),('account_id','=',rec.payment_journal_id.default_account_id.id)])
                    m=sum([m.balance for m in saldos])
            rec.balance = m
            rec.balance_foreign_account=m

    @api.depends('payment_journal_id')
    def verificar_monedas(self):
        for rec in self:

            if self.payment_journal_id.currency_id:
                if self.env.company.currency_id != self.payment_journal_id.currency_id:
                    rec.extranjero = True
                else:
                    rec.extranjero = False
            else:
                rec.extranjero = False



    @api.depends('check_id')
    def ver_cheque(self):
        self.verificar_pago_cheque = False
        if len(self)==1:
            if self.id and self.check_id:
                if not self.check_id.pago_voucher  and not self.check_id.voucher_id :
                    cheque = self.env['account.check'].search([('id', '=', self.check_id.id)])
                    if not cheque.currency_id:
                        moneda=self.currency_id.id
                        cheque.write({
                            'pago_voucher': self.id,
                            'currency_id': moneda
                        })
                        self.verificar_pago_cheque = True
                    else:
                        cheque.write({
                            'pago_voucher': self.id
                        })
                        self.verificar_pago_cheque = True
            else:
                self.verificar_pago_cheque = False

    @api.constrains('check_id')
    def verificar_diario_chequera(self):
        if self.check_id and self.payment_journal_id and self.check_id.checkbook_id:
            if self.check_id.checkbook_id.journal_id  != self.payment_journal_id:
                raise ValidationError('El diario de la chequera %s no coincide con el Metodo de Pago %s. Favor verificar' %(self.check_id.checkbook_id.journal_id.name,self.payment_journal_id.name))


class account_voucher(models.Model):

    _inherit = 'account.payment'



    received_third_check_ids = fields.One2many(
        'account.check.third', 'voucher_id', 'Third Checks',
        domain=[('type', '=', 'third_check')],
        context={'default_type': 'third_check', 'from_voucher': True},
        required=False,
        readonly=True,
        copy=False,
        ondelete='set to null',
        states={'draft': [('readonly', False)]}
        )
    issued_check_ids = fields.One2many(
        'account.check', 'voucher_id', 'Issued Checks',
        domain=[('type', '=', 'issue_check')],
        context={'default_type': 'issue_check', 'from_voucher': True},
        copy=False,
        required=False,
        readonly=True,
        ondelete='set null',
        states={'draft': [('readonly', False)]}
        )
    delivered_third_check_ids = fields.One2many(
        'account.check', 'third_handed_voucher_id',
        'Third Checks', domain=[('type', '=', 'third_check')],
        copy=False,
        context={'from_voucher': True},
        required=False,
        readonly=True,
        ondelete='set null',
        states={'draft': [('readonly', False)]}
        )
    checks_amount = fields.Float(
        _('Importe en Cheques'),
        # waiting for a PR 9081 to fix computed fields translations
        # _('Checks Amount'),
        help='Importe Pagado con Cheques',
        # help=_('Amount Paid With Checks'),
        digits=dp.get_precision('Account'),
    )
    obra = fields.Many2one('stock.warehouse', string='Centro de costo')
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Chequera',
    )
    number = fields.Integer(string="Nro. de cheque")
    current_number = fields.Integer(string="Ultimo numero utilizado", readonly=True)
    diferido = fields.Boolean(compute="check_difer")
    depositado = fields.Boolean(compute="check_difer")

    @api.depends('received_third_check_ids')
    def check_difer(self):
        for rec in self:
            diferidos = rec.received_third_check_ids.filtered(lambda x: x.tipo_cheque == 'diferido')
            if len(diferidos) > 0:
                rec.diferido = True
            else:
                rec.diferido = False
            depositados = rec.received_third_check_ids.filtered(lambda x: x.state == 'deposited')
            if len(depositados) > 0:
                rec.depositado = True
            else:
                rec.depositado = False


    @api.onchange('dummy_journal_id')
    def change_dummy_journal_id(self):
        """Unlink checks on journal change"""
        # if we select checks journal we set net_amount to 0
        if self.journal_id.payment_subtype in ('issue_check', 'third_check'):
            self.net_amount = False
        self.delivered_third_check_ids = False
        self.issued_check_ids = False
        self.received_third_check_ids = False

    def unlink(self):
        if self.received_third_check_ids:
            self.received_third_check_ids.filtered(lambda check: check.state not in ('deposited','rechazado','conciliado')).unlink()
        return super(account_voucher, self).unlink()
    def action_cancel_draft(self):
        res = super(account_voucher, self).action_cancel_draft()
        checks = self.env['account.check'].search(
            [('voucher_id', 'in', self.ids)])
        checks.action_cancel_draft()
        return res



    @api.onchange('checkbook_id')
    def onchange_checkbook(self):
        self.number = self.checkbook_id.next_check_number
        # raise exceptions.ValidationError(self.checkbook_id.id)

    @api.onchange('checkbook_id')
    def _get_current_check_number(self):
        if self.checkbook_id:
            cr = self.env.cr.execute('select max(number) from account_check where checkbook_id =%s',
                                     (self.checkbook_id.id,))
            number = self.env.cr.fetchone()[0]
            if number:
                self.current_number = number
            else:
                self.current_number = 0




    def cancel_voucher(self):
        if self.checkbook_id:
            third_handed_checks = self.env['account.check'].search([
                ('third_handed_voucher_id', 'in', self.filtered(
                    lambda v: v.type == 'payment').ids)])
            for third_check in third_handed_checks:
                if third_check.state != 'handed':
                    raise Warning(_(
                        'You can not cancel handed third checks in states other '
                        'than "handed". First try to change check state.'))
            third_handed_checks.signal_workflow('handed_holding')

            other_checks = self.env['account.check'].search([
                ('voucher_id', 'in', self.ids)])
            #other_checks.check_check_cancellation()

            other_checks.signal_workflow('cancel')
        # checks = self.env['account.check'].search([
        #     '|',
        #     ('voucher_id', 'in', self.ids),
        #     ('third_handed_voucher_id', 'in', self.ids)])
        # checks.check_check_cancellation()
        # checks.signal_workflow('cancel')
            return super(account_voucher, self).cancel_voucher()

    def proforma_voucher(self, cr, uid, ids, context=None):
        res = super(account_voucher, self).proforma_voucher(
            cr, uid, ids, context=None)
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.type == 'payment':
                for check in voucher.issued_check_ids:
                    check.signal_workflow('draft_router')
                for check in voucher.delivered_third_check_ids:
                    check.signal_workflow('holding_handed')
            elif voucher.type == 'receipt':
                for check in voucher.received_third_check_ids:
                    check.signal_workflow('draft_router')
        return res

    # @api.onchange('amount')
    # def _compute_check_amount(self):
    #     if self.monto_retencion:
    #         self.checks_amount = self.amount - self.monto_retencion


    def get_checks_amount(self):
        res = {}
        for voucher in self:
            checks_amount = self.checks_amount
            res[voucher.id] = checks_amount
        return res


    def get_paylines_amount(self):
        res = super(account_voucher, self).get_paylines_amount()
        for voucher in self:
            checks_amount = self.checks_amount
            res[voucher.id] = res[voucher.id] + checks_amount
        return res

    
    def paylines_moves_create(
            self, voucher, move_id, company_currency, current_currency):
        paylines_total = super(account_voucher, self).paylines_moves_create(
            voucher, move_id, company_currency, current_currency)
        checks_total = self.create_check_lines(
            voucher, move_id, company_currency, current_currency)
        return paylines_total + checks_total

    
    def create_check_lines(
            self, voucher, move_id, company_currency, current_currency):
        move_lines = self.env['account.move.line']
        checks = []
        if voucher.payment_subtype == 'third_check':
            if voucher.type == 'payment':
                checks = voucher.delivered_third_check_ids
            else:
                checks = voucher.received_third_check_ids
        elif voucher.payment_subtype == 'issue_check':
            checks = voucher.issued_check_ids
        # Calculate total
        checks_total = 0.0
        name = self.number
        payment_date = self.payment_date
        amount = self.checks_amount
        account = voucher.account_id
        partner = voucher.partner_id
        move_line = move_lines.create(
            self.prepare_move_line(
                voucher, amount, move_id, name, company_currency,
                current_currency, payment_date, account, partner)
        )
        checks_total += move_line.debit - move_line.credit

        return checks_total

class accountPaymentRegister(models.TransientModel):

    _inherit = 'account.payment.register'

    cheque_tercero=fields.Boolean(compute="es_cheque_tercero",store=True)
    monto_cheque_recibo = fields.Float()
    banco_cheque_recibo = fields.Many2one('res.bank')
    banco_cuenta_recibo = fields.Many2one('res.partner.bank')
    numero_cheque_recibo = fields.Char()
    fecha_cheque_recibo = fields.Date()
    fecha_cheque_diferido = fields.Date(string="Fecha de Cobro Cheque",
                                        help="En caso de que el cheque sea diferido este campo debe ser distinto a fecha cheque recibo")
    titular_recibo = fields.Char()
    nro_cuenta_recibo = fields.Char(string="Nro. de Cuenta")
    tipo_de_cheque_recibo = fields.Selection([('diferido', 'Diferido'), ('vista', 'A la vista')])

    @api.depends('journal_id')
    def es_cheque_tercero(self):
        for rec in self:
            if rec.journal_id.payment_subtype:
                if rec.journal_id.payment_subtype == 'third_check':
                    rec.cheque_tercero = True
                else:
                    rec.cheque_tercero = False

            else:
                rec.cheque_tercero = False

    def action_create_payments(self):
        payments = self._create_payments()
        for p in self:
            # res= super(accountPaymentRegister, self).action_create_payments()
            if p.cheque_tercero:
                moneda = p.currency_id.id
                cheque_tercero = self.env['account.check.third'].search(
                    [('number', '=', p.numero_cheque_recibo),
                     ('bank_id', '=', p.banco_cheque_recibo.id)])
                if p.monto_cheque_recibo != 0:
                    monto_cheque_recibo = p.monto_cheque_recibo
                else:
                    monto_cheque_recibo = p.amount
                # _logger.info('teeeest')
                # _logger.info(res)
                if not cheque_tercero:
                    cheque_tercero = self.env['account.check.third']

                    datos = {
                        'number': p.numero_cheque_recibo,
                        'amount': monto_cheque_recibo,
                        # 'issue_date': datetime.strftime(date.today(),"%d/%m/%Y"),
                        'bank_id': p.banco_cheque_recibo.id,
                        'cuit': p.nro_cuenta_recibo,
                        'payment_date': p.fecha_cheque_diferido,
                        'issue_date': p.fecha_cheque_recibo,
                        'tipo_cheque': p.tipo_de_cheque_recibo,
                        'journal_id': p.journal_id.id,
                        'source_partner_id': p.partner_id.id,
                        'owner_name': p.titular_recibo,
                        'currency_id': moneda,
                        'voucher_id':payments[0].id
                    }
                    cheque_tercero.create(datos)
                else:
                    # raise ValidationError('No se puede duplicar numero de Cheque. Cheque nro %s ya existe en el sistema' % p.numero_cheque)
                    datos = {
                        'owner_name': p.titular_recibo,
                        'journal_id': p.journal_id.id,
                        'bank_id': p.banco_cheque_recibo.id,
                        'cuit': p.nro_cuenta_recibo,
                        'payment_date': p.fecha_cheque_diferido,
                        'issue_date': p.fecha_cheque_recibo,
                        'amount': monto_cheque_recibo,
                        'tipo_cheque': p.tipo_de_cheque_recibo,
                        'number': p.numero_cheque_recibo,
                        'currency_id': moneda,
                        'voucher_id': payments[0].id
                    }
                    cheque_tercero.write(datos)

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action


#    def action_create_payments(self):




