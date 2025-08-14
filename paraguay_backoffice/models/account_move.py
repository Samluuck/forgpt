from odoo import fields, models, exceptions, api , _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError,UserError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

_logger = logging.getLogger(__name__)

class ReversalWizard(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super(ReversalWizard, self)._prepare_default_reversal(move)
        for rec in self:
            if move.move_type in ('out_invoice', 'in_invoice'):
                tipo_comprobante = self.env.ref('paraguay_backoffice.tipo_comprobante_3')
                codigo_hechauka = tipo_comprobante.codigo_hechauka
                res.update({'tipo_comprobante':tipo_comprobante.id,
                      'codigo_hechauka':codigo_hechauka,
                            'factura_afectada':move.id,
                            'timbrado':None})
        return res

class ReSequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    @api.depends('move_ids')
    def _compute_first_name(self):
        self.first_name = ""
        for record in self:
            if record.move_ids:
                record.first_name = record.move_ids.mapped('journal_id')[0].code + "/" + str(
                    datetime.now().year) + "/0001"


class accountMoveValidateWizard(models.TransientModel):
    _inherit = "validate.account.move"


    def validate_move(self):
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
        else:
            raise UserError(_("Missing 'active_model' in context."))

        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))
        for move in moves:
            move._post(not self.force_post)
        return {'type': 'ir.actions.act_window_close'}

class fullrecocnile(models.Model):
    _inherit='account.full.reconcile'
    
    # Se hereda la funcion para que no genere el asiento de reversa de diferencia de cambio y que borre el anteiror.
    def unlink(self):
        for rec in self:
            if rec.exchange_move_id:
                to_reverse = rec.exchange_move_id
                rec.exchange_move_id = False
                partials = to_reverse.line_ids.remove_move_reconcile()
                to_reverse.button_cancel()
                to_reverse.unlink()
        return super(models.Model, self).unlink()

class LineasAsientos(models.Model):
    _inherit = 'account.move.line'

    tipo_cuenta = fields.Many2one(related='account_id.user_type_id')
    prioridad = fields.Integer(string="Prioridad", help="Campo para ordenar debe y haber en libro diario",
                               compute='_get_prioridad')
    porcentaje_ganancia = fields.Float(string="% Rent.",compute='_get_rentabilidad')
    costo = fields.Float(string="Costo")
    porcentaje_descuento = fields.Float(string="% Desc. particular")
    tiene_descuento = fields.Boolean(string="Tiene descuento",default=False)
    codigo_hechauka = fields.Integer(related='move_id.tipo_comprobante.codigo_hechauka')
    categoria_cliente = fields.Char(string="Categoría de cliente", compute="_get_categ_clientes",store=False)
    costo_total = fields.Float(string="Costo Total")
    utilidad_total_gs = fields.Float(string="Utilidad Total")
    utilidad_unitaria_gs = fields.Float(string="Utilidad Unitaria")


    def remove_move_reconcile(self):
        for rec in self:
            lineas=self.matched_debit_ids

            # lineas_dif=lineas.filtered(lambda r:r.journal_id==r.company_id.currency_exchange_journal_id)
            partials=self.env['account.partial.reconcile'].search([('debit_move_id','in',(lineas.ids))])


        res=super(LineasAsientos,self).remove_move_reconcile()
        return res

        #remove_move_reconcile

    @api.depends('partner_id.category_id')
    def _get_categ_clientes(self):
        for rec in self:
            string = ","
            if rec.partner_id.parent_id:
                rec.categoria_cliente = string.join(rec.partner_id.parent_id.mapped('category_id.name'))
            else:
                rec.categoria_cliente = string.join(rec.partner_id.mapped('category_id.name'))


    #Se hereda funcion nativa para agregarle los pagos parciales
    def _prepare_reconciliation_partials(self):
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        /!\ The order of records in self is important because the journal items will be reconciled using this order.

        :return: A recordset of account.partial.reconcile.
        '''
        if not self._context.get('has_partial'):
            res=super(LineasAsientos,self)._prepare_reconciliation_partials()
            return res

        else:

            def fix_remaining_cent(currency, abs_residual, partial_amount):
                if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                    return abs_residual
                else:
                    return partial_amount

            debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0))
            credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0))
            debit_line = None
            credit_line = None

            debit_amount_residual = 0.0
            debit_amount_residual_currency = 0.0
            credit_amount_residual = 0.0
            credit_amount_residual_currency = 0.0
            debit_line_currency = None
            credit_line_currency = None
            recibo_residual=0
            partials_vals_list = []

            while True:

                # Move to the next available debit line.



                if not debit_line:
                    debit_line = next(debit_lines, None)
                    if not debit_line:
                        break

                    if self._context.get('recibo') and self._context.get('has_partial'):
                        recibo=self._context.get('recibo')
                        if recibo.tipo=='move':
                            factu=recibo.pagos_facturas_ids.filtered(lambda r:r.invoice_id==debit_line.move_id)
                            debit_amount_residual=min(factu.invoice_id.monto_a_pagar, debit_line.amount_residual_currency)

                        else:
                            factu=recibo.pagos_facturas_ids.filtered(lambda r:r.move_line_id==debit_line)
                            debit_amount_residual=min(factu.monto, debit_line.amount_residual_currency)


                        if debit_line.currency_id:

                            debit_amount_residual_currency = debit_amount_residual
                            tasa=self.env['res.currency.rate'].search([('currency_id','=',debit_line.currency_id.id),('name','=',debit_line.date)])
                            if tasa:
                                debit_amount_residual = debit_amount_residual * tasa[0].set_venta
                            debit_line_currency = debit_line.currency_id
                        else:

                            debit_amount_residual_currency = debit_amount_residual
                            debit_line_currency = debit_line.company_currency_id

                    else:
                        debit_amount_residual = debit_line.amount_residual
                        if debit_line.currency_id:
                            debit_amount_residual_currency = debit_line.amount_residual_currency
                            debit_line_currency = debit_line.currency_id
                        else:
                            debit_amount_residual_currency = debit_amount_residual
                            debit_line_currency = debit_line.company_currency_id

                # Move to the next available credit line.
                if not credit_line:
                    credit_line = next(credit_lines, None)
                    if not credit_line:
                        break
                    if self._context.get('op') and self._context.get('has_partial'):
                        op = self._context.get('op')
                        print('opop')
                        if op.tipo == 'move':
                            factu = op.orden_pagos_facturas_ids.filtered(lambda r: r.invoice_id == credit_line.move_id)
                            credit_amount_residual = -1* min(factu.invoice_id.monto_a_pagar, abs(credit_line.amount_residual_currency))
                        else:
                            factu = op.orden_pagos_facturas_ids.filtered(lambda r: r.move_line_id == credit_line)
                            credit_amount_residual = -1 * min(factu.monto, abs(credit_line.amount_residual_currency))
                        if credit_line.currency_id:
                            print('concurren')
                            print(credit_line.name)
                            print(credit_amount_residual)
                            credit_amount_residual_currency = credit_amount_residual
                            tasa = self.env['res.currency.rate'].search(
                                [('currency_id', '=', credit_line.currency_id.id), ('name', '=', credit_line.date)])
                            if tasa:
                                credit_amount_residual = credit_amount_residual * tasa[0].set_venta
                            print(credit_amount_residual)
                            credit_line_currency = credit_line.currency_id
                        else:
                            credit_amount_residual_currency = credit_amount_residual
                            credit_line_currency = credit_line.company_currency_id
                    else:
                        credit_amount_residual = credit_line.amount_residual



                        if credit_line.currency_id:
                            credit_amount_residual_currency = credit_line.amount_residual_currency
                            credit_line_currency = credit_line.currency_id
                        else:
                            credit_amount_residual_currency = credit_amount_residual
                            credit_line_currency = credit_line.company_currency_id


                min_amount_residual = min(debit_amount_residual, -credit_amount_residual)
                has_debit_residual_left = not debit_line.company_currency_id.is_zero(debit_amount_residual) and debit_amount_residual > 0.0
                has_credit_residual_left = not credit_line.company_currency_id.is_zero(credit_amount_residual) and credit_amount_residual < 0.0
                has_debit_residual_curr_left = not debit_line_currency.is_zero(debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
                has_credit_residual_curr_left = not credit_line_currency.is_zero(credit_amount_residual_currency) and credit_amount_residual_currency < 0.0

                if debit_line_currency == credit_line_currency:
                    # Reconcile on the same currency.

                    # The debit line is now fully reconciled because:
                    # - either amount_residual & amount_residual_currency are at 0.
                    # - either the credit_line is not an exchange difference one.
                    if not has_debit_residual_curr_left and (has_credit_residual_curr_left or not has_debit_residual_left):
                        debit_line = None
                        continue

                    # The credit line is now fully reconciled because:
                    # - either amount_residual & amount_residual_currency are at 0.
                    # - either the debit is not an exchange difference one.
                    if not has_credit_residual_curr_left and (has_debit_residual_curr_left or not has_credit_residual_left):
                        credit_line = None

                        continue


                    min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                    min_debit_amount_residual_currency = min_amount_residual_currency
                    min_credit_amount_residual_currency = min_amount_residual_currency

                else:
                    # Reconcile on the company's currency.

                    # The debit line is now fully reconciled since amount_residual is 0.
                    if not has_debit_residual_left:
                        debit_line = None
                        continue

                    # The credit line is now fully reconciled since amount_residual is 0.
                    if not has_credit_residual_left:
                        credit_line = None

                        continue

                    min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                        min_amount_residual,
                        debit_line.currency_id,
                        credit_line.company_id,
                        credit_line.date,
                    )
                    min_debit_amount_residual_currency = fix_remaining_cent(
                        debit_line.currency_id,
                        debit_amount_residual_currency,
                        min_debit_amount_residual_currency,
                    )
                    min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                        min_amount_residual,
                        credit_line.currency_id,
                        debit_line.company_id,
                        debit_line.date,
                    )
                    min_credit_amount_residual_currency = fix_remaining_cent(
                        credit_line.currency_id,
                        -credit_amount_residual_currency,
                        min_credit_amount_residual_currency,
                    )

                debit_amount_residual -= min_amount_residual
                debit_amount_residual_currency -= min_debit_amount_residual_currency
                credit_amount_residual += min_amount_residual
                credit_amount_residual_currency += min_credit_amount_residual_currency
                """ En caso de que venga de una OP o recibo, y de que el account.payment solo pague parcialmente la factura,
                se actualiza el campo amount de la linea de recibo/op con el saldo parcial que deja el payment
               """
                factura_pago_parcial = self._context.get('factura_parcial')
                if factu and factu.amount == 0 and credit_amount_residual != 0 and factu == factura_pago_parcial:
                    factu.amount = factu.residual - min_amount_residual
                """ En caso de que la diferencia entre la conciliacion y el monto residual sea menor a 0.5, se redondea para dejar
                igual que el monto residual de la deuda en cuestión
                """
                if self._context.get('recibo') and self._context.get('has_partial'):
                    if debit_line.amount_residual_currency - min_credit_amount_residual_currency <= 0.5:
                        min_credit_amount_residual_currency = debit_line.amount_residual_currency
                        min_debit_amount_residual_currency = debit_line.amount_residual_currency
                        min_amount_residual = debit_line.amount_residual


                partials_vals_list.append({
                    'amount': min_amount_residual,
                    'debit_amount_currency': min_debit_amount_residual_currency,
                    'credit_amount_currency': min_credit_amount_residual_currency,
                    'debit_move_id': debit_line.id,
                    'credit_move_id': credit_line.id,
                })
            return partials_vals_list

    @api.onchange('porcentaje_descuento')
    def set_porcentaje_discount(self):
        for rec in self:
            rec.discount = rec.move_id.porcentaje_descuento + rec.porcentaje_descuento
            rec._onchange_price_subtotal()

    @api.depends('price_total','costo')
    def _get_rentabilidad(self):
        for rec in self:
            if rec.costo > 0 and rec.price_total > 0:
                rec.porcentaje_ganancia = ((rec.price_total - rec.costo) / rec.price_total ) * 100
            elif rec.costo == 0 and rec.price_total > 0:
                rec.porcentaje_ganancia = 100
            else:
                rec.porcentaje_ganancia = 0
    @api.depends('debit', 'credit')
    def _get_prioridad(self):
        for rec in self:
            if rec.debit > 0:
                rec.prioridad = 1
            else:
                rec.prioridad = 2
    @api.constrains('account_id', 'journal_id')
    def _check_constrains_account_id_journal_id(self):
        for line in self.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            account = line.account_id
            journal = line.move_id.journal_id

            if account.deprecated:
                raise UserError(_('The account %s (%s) is deprecated.') % (account.name, account.code))

            account_currency = account.currency_id

            if account.allowed_journal_ids and journal not in account.allowed_journal_ids:
                raise UserError(
                    _('You cannot use this account (%s) in this journal, check the field \'Allowed Journals\' on the related account.',
                      account.display_name))

            failed_check = False
            if (journal.type_control_ids - journal.default_account_id.user_type_id) or journal.account_control_ids:
                failed_check = True
                if journal.type_control_ids:
                    failed_check = account.user_type_id not in (
                            journal.type_control_ids - journal.default_account_id.user_type_id)
                if failed_check and journal.account_control_ids:
                    failed_check = account not in journal.account_control_ids

            if failed_check:
                raise UserError(
                    _('You cannot use this account (%s) in this journal, check the section \'Control-Access\' under tab \'Advanced Settings\' on the related journal.',
                      account.display_name))

    @api.constrains('currency_id', 'account_id')
    def _check_currency(self):
        pass


class Asientos(models.Model):
    _inherit = 'account.move'
    '''
        recibe como parametro en el context el valor del campo name para notas de REMISION
    '''
    concepto_asiento = fields.Char(size=70, required=False, string="Concepto")
    diferencia=fields.Float()
    ultima_fecha_pago = fields.Date(string="Ultima fecha de pago", compute="get_ultima_fecha_pago")
    num_asiento = fields.Integer(string='Numero de asiento')


    @api.depends('line_ids.matched_debit_ids','line_ids.matched_credit_ids')
    def get_ultima_fecha_pago(self):
        for rec in self:
            lines = rec.line_ids \
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            partials = [] ###TODO: lista para almacenar todos los pagos y cobros relacionados
            if len(lines.mapped('matched_debit_ids'))>0:
                partials.append(lines.mapped('matched_debit_ids.debit_move_id.date'))
            if len(lines.mapped('matched_credit_ids')) > 0:
                partials.append(lines.mapped('matched_credit_ids.credit_move_id.date'))
            if len(partials) > 0:
                partials[0].sort() ###Se accede a todas las fechas ordenadas
                rec.ultima_fecha_pago = partials[0][-1] #Asignamos el ultimo valor de la lista y obtenemos su fecha
    def _check_balanced(self):
        #   Se hereda esta funcion debido a que tenemos validacion al post
        return

    @api.ondelete(at_uninstall=False)
    def _unlink_forbid_parts_of_chain(self):
        """ Moves with a sequence number can only be deleted if they are the last element of a chain of sequence.
        If they are not, deleting them would create a gap. If the user really wants to do this, he still can
        explicitly empty the 'name' field of the move; but we discourage that practice.
        """
        return True
        # if not self._context.get('force_delete') and not self.filtered(
        #         lambda move: move.name != '/')._is_end_of_seq_chain():
        #     raise UserError(_(
        #         "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. You should probably revert it instead."
        #     ))

    @api.model
    def renumerar_asientos(self, periodo):

        ## EL CAMPO FECHA DEBE SER LA FECHA DE INICIO DE BUSQUEDA YA QUE LUEGO YO LE SACO EL ANHO PARA PODER CONCATENAR CON LA FECHA DE INICIO DEL ANHO Y LA FECHA FINAL DEL ANHO, ASI QUE ES IMPORTANTE QUE LE PONGAS
        # fecha = datetime.strptime(self.date, "%Y-%m-%d")

        anio = periodo
        fecha_start = str(anio) + '-01-01'
        fecha_fin = str(anio) + '-12-31'
        fecha_start = "'" + fecha_start + "'"
        fecha_fin = "'" + fecha_fin + "'"
        cr = self._cr
        cr.execute(
            'select id, date from account_move where date >= %s and date <= %s and state = %s order by date, id' % (
                fecha_start, fecha_fin, "'posted'"))
        asientos = cr.fetchall()

        secuencia = 1
        for asi in asientos:
            asiento = self.env['account.move'].search([('id', '=', asi[0])])

            asiento.write({'num_asiento': secuencia})
            secuencia += 1

    @api.onchange('line_ids')
    def funcion_calculadora(self):
        suma=0
        for l in self.line_ids:
            suma+=l.debit
            suma-=l.credit
        self.diferencia=suma


    def assert_balanced(self):
        return True


    def _post(self, soft=False):

        for move in self:

            if move.move_type in ('out_invoice','out_refund'):
                lineas=move.line_ids.filtered(lambda r: r.product_id)
                for lin in lineas:

                    if move.currency_id != move.company_id.currency_id:
                        rate_currency= self.env['res.currency.rate'].search([('currency_id','=',move.currency_id.id),('name','=',move.invoice_date),('company_id','=',move.company_id.id)])
                        if rate_currency:
                            rate=rate_currency[0].set_venta
                            if rate==0:
                                rate=1
                        else:
                            rate_currency = self.env['res.currency.rate'].search(
                                [('currency_id', '=', move.currency_id.id), ('name', '=', move.invoice_date),
                                ])
                            if rate_currency:
                                rate = rate_currency[0].set_venta
                                if rate == 0:
                                    rate = 1
                            else:
                                rate=1
                    else:
                        rate=1

                    costo = lin.product_id.standard_price

                    costo_total = costo * lin.quantity

                    venta_unitaria = rate * round((lin.price_subtotal / (lin.quantity if lin.quantity!=0 else 1)))
                    venta_total = rate * lin.price_subtotal
                    lin.costo_total = costo_total
                    lin.costo = costo
                    lin.utilidad_total_gs = venta_total - costo_total
                    lin.utilidad_unitaria_gs= venta_unitaria - costo





            user_lock_date = self.company_id._get_user_fiscal_lock_date()

            if move.invoice_date and user_lock_date and move.invoice_date <= user_lock_date:
                raise ValidationError('No se puede cargar documentos con fecha menor a  %s' % user_lock_date)

            tax_lock_date = self.company_id.tax_lock_date

            if move.invoice_date and tax_lock_date  and move.invoice_date <= tax_lock_date:
                raise ValidationError('No se puede cargar documentos con fecha menor a %s' % user_lock_date)

            if move.date and user_lock_date and move.date <= user_lock_date:
                raise ValidationError('No se puede cargar documentos con fecha menor a  %s' % user_lock_date)

            if move.date and tax_lock_date  and move.date <= tax_lock_date:
                raise ValidationError('No se puede cargar documentos con fecha menor a %s' % user_lock_date)


            if move.currency_id != move.company_id.currency_id:
                _logger.info('------MONEDA DIFE--------')
                if not  self._context.get('not_recalculate_currency'):
                    move.with_context(check_move_validity=False)._onchange_currency()
            debit=sum([x.debit for x in move.line_ids])
            credit=sum([x.credit for x in move.line_ids])
            dif=int(debit-credit)
            if dif !=0:
                _logger.info('------ASIENTO DESCUADRADO LINEAS--------')
                for l in move.line_ids:
                    _logger.info('Cuenta')
                    _logger.info(l.account_id.display_name)
                    _logger.info('Debit')
                    _logger.info(l.debit)
                    _logger.info('Credit')
                    _logger.info(l.credit)

                #raise ValidationError('El asiento contable esta descuadrado, favor verificar. La diferencia es de %s' %str(dif))
                if abs(dif) < 4:
                    if dif > 0:
                        linea_credito = move.line_ids.filtered(lambda r: r.credit > 0)
                        if linea_credito:
                            linea_credito[0].credit += abs(dif)
                    else:
                        linea_debito = move.line_ids.filtered(lambda r: r.debit > 0)
                        if linea_debito:
                            linea_debito[0].debit += abs(dif)

                debit = sum([x.debit for x in move.line_ids])
                credit = sum([x.credit for x in move.line_ids])
                dif = int(debit - credit)
                if dif != 0:
                    raise ValidationError(
                        'El asiento contable esta descuadrado, favor verificar. La diferencia es de %s' % str(dif))

        res = super(Asientos, self)._post(soft)
        return res




