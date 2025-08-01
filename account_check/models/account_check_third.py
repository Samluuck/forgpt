# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __odoo__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api,exceptions
from odoo.exceptions import Warning
import logging
import odoo.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class account_check(models.Model):

    _name = 'account.check.third'
    _description = 'Account Check Third'
    _order = "id desc"
    _inherit = ['mail.thread']

    pago_voucher = fields.Many2one('account.voucher', string="Pago",tracking=True)
    type = fields.Selection([('third_check', 'Cheque de Terceros'), ('issue_check', 'Cheques Propios')],
                            compute='obtener_tipo', store=True, string='Tipo')
    journal_id = fields.Many2one('account.journal', compute='obtener_tipo', string='Diario')

    cuenta_origen = fields.Many2one('account.account', string="Cuenta", compute="_obtener_cuenta",store=True)


    @api.depends('voucher_id', 'voucher_id.state', 'pago_voucher', 'pago_voucher.state')
    def obtener_tipo(self):
        for rec in self:
            if rec.pago_voucher:
                rec.type = rec.pago_voucher.payment_journal_id.payment_subtype
                rec.journal_id = rec.pago_voucher.payment_journal_id

            elif rec.voucher_id:
                rec.type = rec.voucher_id.journal_id.payment_subtype
                rec.journal_id = rec.voucher_id.journal_id.id
            else:
                rec.type = False
                rec.journal_id = False



    @api.depends('voucher_id', 'pago_voucher')
    def _obtener_cuenta(self):
        for rec in self:
            if rec.pago_voucher:
                rec.cuenta_origen = rec.pago_voucher.payment_journal_id.default_account_id
            elif rec.voucher_id:
                rec.cuenta_origen = rec.voucher_id.journal_id.default_account_id


    @api.depends('number')
    def _get_name(self):
        self.name = self.number


    @api.depends(
        'voucher_id',
        'voucher_id.partner_id',
        'type',
        'third_handed_voucher_id',
        'third_handed_voucher_id.partner_id',
        )
    def _get_destiny_partner(self):
        partner_id = False
        if self.type == 'third_check' and self.third_handed_voucher_id:
            partner_id = self.third_handed_voucher_id.partner_id.id
        elif self.type == 'issue_check':
            partner_id = self.voucher_id.partner_id.id
        self.destiny_partner_id = partner_id


    @api.depends(
        'voucher_id',
        'voucher_id.partner_id',
        'pago_voucher',
        'pago_voucher.partner_id',
        'type',
    )
    def _get_source_partner(self):
        partner_id = False
        if self.type == 'third_check':
            if self.voucher_id:
                partner_id = self.voucher_id.partner_id.id
        if self.pago_voucher:
            partner_id = self.pago_voucher.partner_id.id
        self.source_partner_id = partner_id




    @api.depends('number')
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
        if self.type == 'third_check':
            partner_id = self.voucher_id.partner_id.id
        self.source_partner_id = partner_id

    name = fields.Char(
        compute='_get_name',
        string=_('Número')
        )
    number = fields.Integer(
        _('Numero'),
        required=True,
        readonly=True,
        states={'handed': [('readonly', False)]},
        copy=False
        )
    amount = fields.Float(
        'Monto',
        required=True,
        readonly=True,
        digits=dp.get_precision('Account'),
        states={'handed': [('readonly', False)]},
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
        ondelete='set null',
        )
    # type = fields.Selection(
    #     related='voucher_id.journal_id.payment_subtype',
    #     string='Tipo',
    #     readonly=True,
    #     store=True
    #     )
    recibo = fields.Char(string="Nro. de recibo")
    # journal_id = fields.Many2one(
    #     'account.journal',
    #     related='voucher_id.journal_id',
    #     string='Diario',
    #     readonly=True,
    #     store=True
    #     )
    issue_date = fields.Date(
        'Fecha de Emision',
        required=False,
        readonly=True,
        states={'handed': [('readonly', False)]},
        default=fields.Date.context_today,
        )
    payment_date = fields.Date(
        'Fecha de pago',
        readonly=True,
        help="Only if this check is post dated",
        states={'handed': [('readonly', False)]}
        )
    destiny_partner_id = fields.Many2one(
        'res.partner',
        compute='_get_destiny_partner',
        string='Destino',
        store=True,
        )
    current_number = fields.Integer(string="Ultimo numero utilizado",readonly=True)
    user_id = fields.Many2one(
        'res.users',
        'Usario',
        readonly=True,
        default=lambda self: self.env.user,
        )
    payment_amount = fields.Float('Monto de la orden de pago:',compute='_compute_amount')
    retencion_amount = fields.Float('Monto de las retenciones:',compute='_compute_retenciones')
    facturas_asociadas = fields.One2many(string="Facturas asociadas",compute='_compute_facturas')
    clearing = fields.Selection([
            ('24', '24 hs'),
            ('48', '48 hs'),
            ('72', '72 hs'),
        ],
        'Clearing',
        readonly=True,
        states={'handed': [('readonly', False)]})
    state = fields.Selection([
            ('handed', 'En mano'),
            ('deposited', 'Depositado'),
            ('conciliado', 'Conciliado'),
            ('rechazado','Rechazado'),
            ('cancel', 'Anulado'),
        ],
        'State',
        required=True,
        tracking=True,
        default='handed',
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
        default=lambda self: self.env.company,
        string='Company',
        store=True,
        readonly=True
        )


    debit_account_move_id = fields.Many2one(
        'account.move',
        'Asiento contable de débito',
        readonly=True,
        copy=False,
        )

    # Third check
    third_handed_voucher_id = fields.Many2one(
        'account.payment', 'Handed Voucher', readonly=True,)
    source_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente'
        )
    customer_reject_debit_note_id = fields.Many2one(
        'account.move',
        'Customer Reject Debit Note',
        readonly=True,
        copy=False
        )
    bank_id = fields.Many2one(
        'res.bank', 'Banco',
        required=True,
        readonly=True,
        states={'handed': [('readonly', False)]}
        )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda'
        )
    vat = fields.Char(
        # TODO rename to Owner VAT
        'Owner Vat',
        readonly=True,
        states={'handed': [('readonly', False)]}
        )
    owner_name = fields.Char(
        'Propietario',
        readonly=True,
        states={'handed': [('readonly', False)]}
        )
    deposit_account_move_id = fields.Many2one(
        'account.move',
        'Asiento contable de depósito',
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

    # def _check_number_interval(self, cr, uid, ids, context=None):
    #     for obj in self.browse(cr, uid, ids, context=context):
    #         if obj.type != 'issue_check' or (
    #                 obj.checkbook_id and
    #                 obj.checkbook_id.range_from <= obj.number <=
    #                 obj.checkbook_id.range_to):
    #             return True
    #     return False
    #
    # def _check_number_issue(self, cr, uid, ids, context=None):
    #     for obj in self.browse(cr, uid, ids, context=context):
    #         if obj.type == 'issue_check':
    #             same_number_check_ids = self.search(
    #                 cr, uid, [
    #                     ('id', '!=', obj.id),
    #                     ('number', '=', obj.number),
    #                     ('checkbook_id', '=', obj.checkbook_id.id)],
    #                 context=context)
    #             if same_number_check_ids:
    #                 return False
    #     return True
    #
    # 
    # def _def_default_amount(self):
    #     return self.payment_amount
    # def _check_number_third(self, cr, uid, ids, context=None):
    #     for obj in self.browse(cr, uid, ids, context=context):
    #         if obj.type == 'third_check':
    #             same_number_check_ids = self.search(
    #                 cr, uid, [
    #                     ('id', '!=', obj.id),
    #                     ('number', '=', obj.number),
    #                     ('voucher_id.partner_id', '=',
    #                         obj.voucher_id.partner_id.id)], context=context)
    #             if same_number_check_ids:
    #                 return False
    #     return True

    """ _constraints = [
        (_check_number_issue,
            'Check Number must be unique per Checkbook!',
            ['number', 'checkbook_id', 'type']),
        (_check_number_third,
            'Check Number must be unique per Owner and Bank!',
            ['number', 'bank_id', 'owner_name', 'type']),
    ]"""





    @api.depends('voucher_id')
    def _compute_amount(self):
        self.payment_amount = self.voucher_id.amount;






    @api.onchange('issue_date', 'payment_date')
    def onchange_date(self):
        if self.issue_date and self.payment_date:
            if self.issue_date > self.payment_date:
                self.payment_date = False
                raise Warning(
                    _('La Fecha de Pago debe Ser mayor o igual que la fecha de emision'))

    @api.onchange('voucher_id')
    def onchange_voucher(self):
        self.vat = self.voucher_id.partner_id.vat


    def unlink(self):
        for rec in self:
            if rec.state not in ('handed','cancel'):
                raise Warning(
                _('El cheque debe estar en estado en mano para poder eliminarse'))
        return super(account_check, self).unlink()




    def action_cancel_handed(self):
        # go from canceled state to handed state
        self.write({'state': 'handed'})
        self.delete_workflow()
        self.create_workflow()
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


    def action_handed(self):
        self.state = 'handed'


    def action_validado(self):
        self.state = 'validado'

   


    def action_sign(self):
        self.state = 'signed'


    def action_handed_signed(self):
        self.state = 'signed'


    def action_signed_validado(self):
        self.state = 'validado'


    def action_validado_handed(self):
        self.state = 'handed'


    def action_reject(self):
        self.write({'state': 'rejected'})
        return True




    def action_conciliar(self):
        self.write({'state': 'conciliado'})
        return True


    def action_rechazar(self):
        self.write({'state': 'rechazado'})
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
                    'handed', 'handed']:
                raise Warning(_(
                    'You can not cancel issue checks in states other than '
                    '"handed or "handed". First try to change check state.'))
            # third checks received
            elif check.type == 'third_check' and check.state not in [
                    'handed', 'holding']:
                raise Warning(_(
                    'You can not cancel third checks in states other than '
                    '"handed or "holding". First try to change check state.'))
            elif check.type == 'third_check' and check.third_handed_voucher_id:
                raise Warning(_(
                    'You can not cancel third checks that are being used on '
                    'payments'))
        return True


    def action_cancel(self):
        for check in self:

            if check.deposit_account_move_id:
                raise Warning(_(
                    'Para cancelar un cheque depositado primero deben eliminarse todos los asientos asociados '
                    ))
            else:
                self.write({'state': 'cancel'})

