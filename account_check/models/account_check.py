# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api,exceptions
from odoo.exceptions import Warning,ValidationError
import logging
import odoo.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class account_check(models.Model):

    _name = 'account.check'
    _description = 'Account Check'
    _order = "id desc"
    _inherit = ['mail.thread']

    pago_voucher = fields.Many2one('account.voucher', string="Pago",tracking=True)
    type = fields.Selection([('third_check', 'Cheque de Terceros'), ('issue_check', 'Cheques Propios')],
                            compute='obtener_tipo', store=True, string='Tipo',default='issue_check')
    journal_id = fields.Many2one('account.journal',compute='obtener_tipo', string='Diario',store=True)


    @api.depends('voucher_id', 'voucher_id.state', 'pago_voucher', 'pago_voucher.state')
    def obtener_tipo(self):
        for rec in self:
            if rec.pago_voucher:
                rec.type = rec.pago_voucher.payment_journal_id.payment_subtype
                rec.journal_id = rec.pago_voucher.payment_journal_id

            elif rec.voucher_id:
                rec.type = rec.voucher_id.journal_id.payment_subtype
                rec.journal_id = rec.voucher_id.journal_id
            else:
                rec.type='issue_check'


    @api.depends(
        'voucher_id',
        'pago_voucher',
        'voucher_id.partner_id',
        'pago_voucher.partner_id',
        'type',
        'third_handed_voucher_id',
        'third_handed_voucher_id.partner_id',
    )
    def _get_destiny_partner(self):
        partner_id = False
        if self.type == 'third_check' and self.third_handed_voucher_id:
            partner_id = self.third_handed_voucher_id.partner_id.id
        elif self.type == 'issue_check':
            if self.voucher_id:
                partner_id = self.voucher_id.partner_id.id

            elif self.pago_voucher:
                partner_id = self.pago_voucher.partner_id.id
        self.destiny_partner_id = partner_id

    
    def _get_checkbook(self):
        journal_id = self._context.get('default_journal_id', False)
        payment_subtype = self._context.get('default_type', False)
        if journal_id and payment_subtype == 'issue_check':
            checkbooks = self.env['account.checkbook'].search(
                [('state', '=', 'active'), ('journal_id', '=', journal_id)])
            return checkbooks and checkbooks[0] or False


    @api.depends('number', 'checkbook_id', 'checkbook_id.padding')
    def _get_name(self):
        for rec in self:
            rec.name = rec.number


    @api.depends(
        'voucher_id',
        'voucher_id.partner_id',
        'type',
        'third_handed_voucher_id',
        'third_handed_voucher_id.partner_id',
        )
    def _get_destiny_partner(self):
        for rec in self:
            partner_id = False
            if rec.type == 'third_check' and rec.third_handed_voucher_id:
                partner_id = rec.third_handed_voucher_id.partner_id.id
            elif rec.type == 'issue_check':
                partner_id = rec.voucher_id.partner_id.id
            rec.destiny_partner_id = partner_id


    @api.depends(
        'voucher_id',
        'voucher_id.partner_id',
        'type',
        )
    def _get_source_partner(self):
        partner_id = False
        for rec in self:
            if rec.type == 'third_check':
                partner_id = rec.voucher_id.partner_id.id
            rec.source_partner_id = partner_id

    name = fields.Char(
        compute='_get_name',
        string=_('Nro'),
        store=True
        )
    number = fields.Integer(
        _('Numero'),
        states={'draft': [('readonly', False)]},
        copy=False
        )
    amount = fields.Float(
        'Monto',
        required=True,
        readonly=True,
        digits=dp.get_precision('Account'),
        states={'draft': [('readonly', False)]},
        )
    company_currency_amount = fields.Float(
        'Company Currency Amount',
        readonly=True,
        digits=dp.get_precision('Account'),
        help='This value is only set for those checks that has a different '
        'currency than the company one.'
        )
    voucher_id = fields.Many2one(
        'account.payment',
        'Pago',
        readonly=True,
        required=False,tracking=True,
        ondelete='cascade',
    )
    # type = fields.Selection([('issue_check', 'Cheque Propio'), ('third_check', 'Cheque de Tercero')],
        #related='voucher_id.journal_id.payment_subtype',
        # string='Tipo'
        #readonly=False,
        #store=True
        # )
    recibo = fields.Char(string="Nro. de recibo")
    # journal_id = fields.Many2one(
    #     'account.journal',
    #     related='voucher_id.journal_id',
    #     string='Journal',
    #     readonly=True,
    #     store=True
    #     )
    comentario = fields.Text(string="Comentario",tracking=True)
    issue_date = fields.Date(
        'Fecha de Emision',
        required=False,
        readonly=True,
        tracking=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
        )
    payment_date = fields.Date(
        'Fecha de Pago',
        readonly=True,
        tracking=True,
        help="Only if this check is post dated",
        states={'draft': [('readonly', False)]}
        )
    destiny_partner_id = fields.Many2one(
        'res.partner',
        compute='_get_destiny_partner',
        string='Receptor',
        store=True,
        )
    current_number = fields.Integer(string="Ultimo numero utilizado",readonly=True)
    user_id = fields.Many2one(
        'res.users',
        'Usuario',
        readonly=True,
        default=lambda self: self.env.user,
        )
    orden_de = fields.Char(string="A la orden de")
    payment_amount = fields.Float('Monto de la orden de pago:',compute='_compute_amount')
    clearing = fields.Selection([
            ('24', '24 hs'),
            ('48', '48 hs'),
            ('72', '72 hs'),
        ],
        'Clearing',
        readonly=True,
        states={'draft': [('readonly', False)]})
    state = fields.Selection([
            ('draft', 'Emitido'),
            ('validado','Verificado'),
            ('signed', 'Signed'),
            ('handed', 'Handed'),
            ('conciliado', 'Conciliado'),
            ('cancel', 'Anulado'),
        ],
        'Estado',
        required=True,
        tracking=True,
        default='draft',
        copy=False,
        )
    supplier_reject_debit_note_id = fields.Many2one(
        'account.move',
        'Supplier Reject Debit Note',
        readonly=True,
        copy=False,
        )
    expense_account_move_id = fields.Many2one(
        'account.move',
        'Expense Account Move',
        readonly=True,
        copy=False,
        )
    replacing_check_id = fields.Many2one(
        'account.check',
        'Replacing Check',
        readonly=True,
        copy=False,
        )

    # Related fields
    company_id = fields.Many2one(
        'res.company',

        string='Compania',
        default=lambda self: self.env.company,
        store=True
        )

    # Issue Check
    issue_check_subtype = fields.Selection(
        related='checkbook_id.issue_check_subtype',
        string='Subtype',
        readonly=True, store=True
        )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Chequera',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=_get_checkbook,
        )
    debit_account_move_id = fields.Many2one(
        'account.move',
        'Debit Account Move',
        copy=False,
        store =True
        )

    # Third check
    third_handed_voucher_id = fields.Many2one(
        'account.payment', 'Handed Voucher', readonly=True,)
    source_partner_id = fields.Many2one(
        'res.partner',
        compute='_get_source_partner',
        string='Emisor',
        store=True,
        )
    customer_reject_debit_note_id = fields.Many2one(
        'account.move',
        'Customer Reject Debit Note',
        readonly=True,
        copy=False
        )
    bank_id = fields.Many2one(
        'res.bank', 'Banco',
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',

        default=lambda self: self.env.company.currency_id,
        )
    vat = fields.Char(
        # TODO rename to Owner VAT
        'Propietario Vat',
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    owner_name = fields.Char(
        'Nombre del Propietario',
        readonly=True,
        states={'draft': [('readonly', False)]}
        )
    deposit_account_move_id = fields.Many2one(
        'account.move',
        'Asiento de Deposito',
        readonly=True,
        copy=False
        )
    # account move of return
    return_account_move_id = fields.Many2one(
        'account.move',
        'Return Account Move',
        readonly=True,
        copy=False
        )

    tiene_fact_cred = fields.Boolean(compute='_verificar_fact')

    @api.depends('voucher_id','pago_voucher')
    def _verificar_fact(self):
        for rec in self:
            if rec.voucher_id:
                if rec.voucher_id.orden_pago_id:
                    if any(f.tipo_factura == 2 for f in rec.voucher_id.orden_pago_id.orden_pagos_facturas_ids.mapped('invoice_id')):
                        rec.tiene_fact_cred = True
                    else:
                        rec.tiene_fact_cred = False
                else:
                    rec.tiene_fact_cred = False
            else:
                rec.tiene_fact_cred = False
    
    def _check_number_interval(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.type != 'issue_check' or (
                    obj.checkbook_id and
                    obj.checkbook_id.range_from <= obj.number <=
                    obj.checkbook_id.range_to):
                return True
        return False
    
    def _check_number_issue(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.type == 'issue_check':
                same_number_check_ids = self.search(
                    cr, uid, [
                        ('id', '!=', obj.id),
                        ('number', '=', obj.number),
                        ('checkbook_id', '=', obj.checkbook_id.id)],
                    context=context)
                if same_number_check_ids:
                    return False
        return True

    
    def _def_default_amount(self):
        return self.payment_amount
    def _check_number_third(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.type == 'third_check':
                same_number_check_ids = self.search(
                    cr, uid, [
                        ('id', '!=', obj.id),
                        ('number', '=', obj.number),
                        ('voucher_id.partner_id', '=',
                            obj.voucher_id.partner_id.id)], context=context)
                if same_number_check_ids:
                    return False
        return True

    """ _constraints = [
        (_check_number_issue,
            'Check Number must be unique per Checkbook!',
            ['number', 'checkbook_id', 'type']),
        (_check_number_third,
            'Check Number must be unique per Owner and Bank!',
            ['number', 'bank_id', 'owner_name', 'type']),
    ]"""

    @api.constrains('number')
    def _verificar_duplicado(self):
        if self.number:
            numero = self.env['account.check'].search(
                [('number', '=', self.number), ('checkbook_id', '=', self.checkbook_id.id)])

            if len(numero) > 1:
                raise ValidationError(
                    'El numero de cheque %s de la chequera %s ya se encuentra cargada. Favor verificar' % (
                    str(self.number), str(self.checkbook_id.name)))

    @api.onchange('checkbook_id')
    def _get_current_check_number(self):
        #self.type = 'issue_check'
        if self.checkbook_id.id:
            cr = self.env.cr.execute('select max(number) from account_check where checkbook_id =%s', (self.checkbook_id.id,))
            number = self.env.cr.fetchone()[0]
            if number:
                self.current_number = number
            else:
                self.current_number = 0


    def imprimir(self):
        #self.write({'printed': True})
        a =1
    @api.depends('voucher_id')
    def _compute_amount(self):
        self.payment_amount = self.voucher_id.amount;





    #
    @api.onchange('issue_date', 'payment_date')
    def onchange_date(self):
        if (
                self.issue_date and self.payment_date and
                self.issue_date > self.payment_date):
            self.payment_date = False
            raise Warning(
                _('La Fecha de Pago debe ser mayor o igual a la fecha de Emision'))

    #
    @api.onchange('voucher_id')
    def onchange_voucher(self):
        self.owner_name = self.voucher_id.partner_id.name
        self.vat = self.voucher_id.partner_id.vat
        self.currency_id = self.voucher_id.currency_id

    #
    #@api.onchange('number')
    #def _onchange_number(self):
        # if self.number > 0 and (self.number > self.checkbook_id.range_to or self.number < self.checkbook_id.range_from):
            # raise ValidationError(_('El cheque Nro. %s se encuentra fuera del rango de cheques asignados a la chequera') % self.number)



    def unlink(self):
        if self.state not in ('draft','cancel'):
            raise Warning(
                _('El cheque debe estar en estado emitido para borrar!'))
        return super(account_check, self).unlink()

    @api.onchange('checkbook_id')
    def onchange_checkbook(self):
            self.number = self.checkbook_id.next_check_number
            if self.checkbook_id:
                self.currency_id=self.checkbook_id.debit_journal_id.currency_id.id or self.env.company.currency_id.id
           # raise exceptions.ValidationError(self.checkbook_id.id)



    def action_cancel_draft(self):
        # go from canceled state to draft state
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True


    def action_borrador(self):
        self.write({'state': 'draft'})
        if self.debit_account_move_id:
            for m in self.debit_account_move_id.line_ids:
                if m.full_reconcile_id:
                    m.full_reconcile_id.partial_reconcile_ids.unlink()
                m.remove_move_reconcile()
            self.debit_account_move_id.button_cancel()
            self.debit_account_move_id.unlink()
        return True


    def action_hold(self):
        self.write({'state': 'holding'})
        return True


    def action_deposit(self):
        self.write({'state': 'deposited'})
        return True


    def action_return(self):
        self.write({'state': 'returned'})
        return True


    def action_change(self):
        self.write({'state': 'changed'})
        return True


    def action_hand(self):
        existe_credito = False
        facturas = self.voucher_id.fac_ids
        for factura in facturas:
            if factura.tipo_factura == 2:
                existe_credito = True
        if existe_credito == True:
            if not self.recibo:
                raise Warning(('Debe cargarse un numero de recibo para dar como entregado el cheque'))
            else:
                self.write({'state': 'handed'})
        else:
                self.write({'state': 'handed'})


    def action_draft(self):
        self.state = 'draft'


    def action_validado(self):
        self.state = 'validado'


    def action_sign(self):
        self.state = 'signed'


    def action_reject(self):
        self.write({'state': 'rejected'})
        return True


    def action_conciliar(self):
        self.write({'state': 'conciliado'})
        return True


    def action_cancel_rejection(self):
        for check in self:
            if check.customer_reject_debit_note_id:
                raise Warning(_(
                    'To cancel a rejection you must first delete the customer '
                    'reject debit note!'))
            if check.supplier_reject_debit_note_id:
                raise Warning(_(
                    'To cancel a rejection you must first delete the supplier '
                    'reject debit note!'))
            if check.expense_account_move_id:
                raise Warning(_(
                    'To cancel a rejection you must first delete Expense '
                    'Account Move!'))
            check.signal_workflow('cancel_rejection')
        return True


    def action_cancel_debit(self):
        for check in self:
            if check.debit_account_move_id:
                raise Warning(_(
                    'To cancel a debit you must first delete Debit '
                    'Account Move!'))
            check.signal_workflow('debited_handed')
        return True


    def action_cancel_deposit(self):
        for check in self:
            if check.deposit_account_move_id:
                raise Warning(_(
                    'To cancel a deposit you must first delete the Deposit '
                    'Account Move!'))
            check.signal_workflow('cancel_deposit')
        return True


    def action_cancel_return(self):
        for check in self:
            if check.return_account_move_id:
                raise Warning(_(
                    'To cancel a deposit you must first delete the Return '
                    'Account Move!'))
            check.signal_workflow('cancel_return')
        return True

    # TODO implementar para caso issue y third
    #
    # def action_cancel_change(self):
    #     for check in self:
    #         if check.replacing_check_id:
    #             raise Warning(_(
    #                 'To cancel a return you must first delete the replacing '
    #                 'check!'))
    #         check.signal_workflow('cancel_change')
    #     return True


    def check_check_cancellation(self):
        for check in self:
            if check.type == 'issue_check' and check.state not in [
                    'draft', 'handed']:
                raise Warning(_(
                    'You can not cancel issue checks in states other than '
                    '"draft or "handed". First try to change check state.'))
             #third checks received
            elif check.type == 'third_check' and check.state not in [
                    'draft', 'holding']:
                raise Warning(_(
                    'You can not cancel third checks in states other than '
                    '"draft or "holding". First try to change check state.'))
            elif check.type == 'third_check' and check.third_handed_voucher_id:
                raise Warning(_(
                    'You can not cancel third checks that are being used on '
                    'payments'))
        return True


    def action_cancel(self):
        for check in self:
            if check.type == 'issue_check' and check.state not in [
                'draft', 'handed']:
                raise Warning(_(
                    'You can not cancel issue checks in states other than '
                    '"draft or "handed". First try to change check state.'))
            elif check.debit_account_move_id:
                raise Warning(_(
                    'To cancel a debit you must first delete Debit '
                    'Account Move!'))
            else:
                self.write({'state': 'cancel'})

    @api.constrains('number')
    def verificar_rango_chequera(self):
        if self.number:
            if self.checkbook_id:
                if self.number > self.checkbook_id.range_to:
                    raise ValueError('El cheque nro "%s" es mayor que del ultimo numero  de la chequera %s, con numero de finalizacion= %s. Favor verificar'%(str(self.number),self.checkbook_id.name, str(self.checkbook_id.range_to)))
                if self.number < self.checkbook_id.range_from:
                    raise ValueError('El cheque nro "%s" es menor que del primer numero  de la chequera %s, con numero de inicial= %s. Favor verificar'%(str(self.number),self.checkbook_id.name, str(self.checkbook_id.range_from)))
            else:
                raise ValueError('No posee chequera asociada al cheque, favor agregar')
