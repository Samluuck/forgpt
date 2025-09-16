# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api,_
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero
import logging
import warnings

_logger = logging.getLogger(__name__)


class accountMove(models.Model):
    _inherit = 'account.move'
    ruc_factura = fields.Char(string="RUC", compute='_compute_RUC')
    timbrado = fields.Char(required=False, string="Timbrado", size=8,tracking=True)
    suc = fields.Char(string="Suc", size=3,copy=False,tracking=True)
    sec = fields.Char(string="Sec", size=3,copy=False,tracking=True)
    nro = fields.Char(string="Nro", size=7,copy=False,tracking=True)
    retencion = fields.Boolean(string="Posee Retencion", default=False)
    tipo_comprobante = fields.Many2one('ruc.tipo.documento', string='Tipo comprobante',tracking=True)
    nro_factura = fields.Char(string="Nro. de factura",copy=False,tracking=True)
    tipo_factura = fields.Selection([('1', 'Contado'), ('2', 'Credito')],tracking=True)
    # codigo_hechauka = fields.Integer(related='tipo_comprobante.codigo_hechauka',store=True)
    codigo_hechauka = fields.Integer(string="Codigo Hechauka",related='tipo_comprobante.codigo_hechauka')
    cantidad_cuotas = fields.Integer(string="Cantidad de cuotas",default=0)
    motiv_anulacion = fields.Many2one('ruc.motivo.anulacion', string="Motivo de la anulación")
    guardado = fields.Boolean(default=False)
    monto_retencion = fields.Monetary(string="Monto de la retencion a Pagar/Cobrar", default=0)
    residual_retencion = fields.Monetary(string="Saldo retencion", default=0)
    monto_parcial = fields.Float(string="Monto a Pagar/Cobrar")
    autofactura = fields.Char(string='Autofactura a nombre de:')
    tipo_talonario = fields.Integer(string="Codigo para talonarios",compute="cod_tal")
    tipo_de_documento = fields.Char(string="Tipo para Nota de Credito",compute="verificar_tipo")
    tipo_compra = fields.Selection([('exportacion','Exportacion'),('directo','Directo'),('indirecto','Indirecto'),('indefinido','Indefinido')],string="Tipo de Compra",default='indefinido')
    date_invoice = fields.Date(default=lambda self: fields.Date.context_today(self))
    factura_afectada = fields.Many2one('account.move', string="Factura afectada",domain="[('partner_id', '=', partner_id),('move_type','=',tipo_de_documento),('codigo_hechauka','=',1)]")
    linea_asiento_afectada_nc = fields.Many2one('account.move.line', string="Linea de Asiento afectada",domain="[('partner_id', '=', partner_id)]")
    linea_asiento_afectada_nc_timbrado = fields.Char('Timbrado de Linea Afectada')
    no_mostrar_libro_iva=fields.Boolean()
    invoice_picking_id = fields.Many2one('stock.picking')
    partner_no_despachante = fields.Many2one('res.partner', string='Emisor Factura')
    second_account_debt = fields.Many2one('account.account', string="Cuenta Secundaria", tracking=True)
    @api.constrains('talonario_factura')
    def check_debito_cons(self):
        for rec in self:
            if rec.move_type == 'in_invoice':
                if rec.tipo_comprobante:
                    if rec.tipo_comprobante.codigo_hechauka == 2 and rec.talonario_factura:
                        raise ValidationError('Las notas de debito recibidas no deben poseer talonario de facturas')

    def unlink(self):
        for rec in self:
            if rec.move_type not in ('entry','out_receipt','in_receipt','in_invoice','in_refund'):
                if rec.nro_factura:
                    raise ValidationError('No se puede borrar una factura y/o nota de crédito emitida')
        super(accountMove, self).unlink()



    @api.onchange('factura_afectada')
    def setear_linea_asiento(self):
        for rec in self:
            if rec.factura_afectada:
                payable_or_receivable_line=rec.factura_afectada.line_ids.filtered(lambda r:r.account_internal_type in ('payable','receivable'))
                rec.linea_asiento_afectada_nc_timbrado=rec.factura_afectada.timbrado
                if len(payable_or_receivable_line)==1:
                    rec.linea_asiento_afectada_nc=payable_or_receivable_line[0]

    @api.constrains('timbrado')
    def _check_timbrado(self):
        for rec in self:
            if rec.timbrado:
                if not rec.partner_id.country_id:
                    if len(rec.timbrado) < 8:
                        raise ValidationError('Favor registrar timbrado con 8 dígitos')

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        return True

    def action_invoice_draft(self):
        res = super(invoice_ruc, self).action_invoice_draft()
        if self.user_has_groups('account.group_account_manager'):
            self.move_name = None
        return res


    @api.onchange('tipo_comprobante')
    def cod_hecha(self):
        if self.tipo_comprobante:
            self.codigo_hechauka = self.tipo_comprobante.codigo_hechauka

    @api.depends('partner_id','move_type')
    # @api.one
    def verificar_tipo(self):
        if self.move_type == 'in_invoice' or self.move_type == 'in_refund':
            self.tipo_de_documento='in_invoice'
        else:
            self.tipo_de_documento='out_invoice'

    # @api.multi
    #def name_get(self):
    def _get_move_display_name(self, show_ref=False):
        self.ensure_one()
        name = ''
        if self.state == 'draft':
            name += {
                'out_invoice': _('FV Borrador'),
                'out_refund': _('NCV Borrador'),
                'in_invoice': _('FC Borrador'),
                'in_refund': _('NCC Borrador'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Entrada Borrador'),
            }[self.move_type]
            name += ' '
        if self.nro_factura:
            name += self.nro_factura
        elif not self.name or self.name == '/':
            name += '(* %s)' % str(self.id)

        else:
            name += self.name
        return name + (show_ref and self.ref and ' (%s%s)' % (self.ref[:50], '...' if len(self.ref) > 50 else '') or '')
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('nro_factura', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('nro_factura', operator, name)] + args, limit=limit)
        return recs.name_get()

    # @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']
        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            if not inv.date_due:
                inv.with_context(ctx).write({'date_due': inv.date_invoice})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.nro_factura or '/'
            if inv.payment_term_id:
                totlines = \
                inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total,
                                                                                                            inv.date_invoice)[
                    0]
                res_amount_currency = total_currency
                ctx['date'] = inv._get_currency_rate_date()
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:

                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:

                        amount_currency = False

                    # last line: add the diff

                    # res_amount_currency -= amount_currency or 0

                    if inv.payment_term_id.line_ids.filtered(lambda r: r.value =='instalment'):
                        if i + 1 == len(totlines):


                            # amount_currency += res_amount_currency
                            if t[1] < 0:
                                sumar = inv.amount_total + (round(res_amount_currency, 2) * len(totlines))
                                amount_currency += res_amount_currency - sumar
                            else:
                                sumar = inv.amount_total - (round(res_amount_currency, 2) * len(totlines))
                                amount_currency += res_amount_currency + sumar

                        elif inv.currency_id != company_currency:
                            rate = self.env['res.currency.rate'].search([('name','=',inv.invoice_date),('currency_id','=',inv.currency_id.id)])
                            cotizacion = rate[0].set_venta
                            amount_currency += t[1] / cotizacion
                            res_amount_currency -= amount_currency or 0

                        # else:


                    else:
                        if i + 1 == len(totlines):

                            amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            context = dict(self.env.context)
            # Within the context of an invoice,
            # this default value is for the type of the invoice, not the type of the asset.
            # This has to be cleaned from the context before creating the asset,
            # otherwise it tries to create the asset with the type of the invoice.
            context.pop('default_type', None)
            inv.invoice_line_ids.with_context(context).asset_create()
        return True

    def _get_invoice_computed_reference(self):
        for rec in self:
            if rec.nro_factura:
                res=rec.nro_factura
            else:
                res=super(accountMove,self)._get_invoice_computed_reference()
        return res
    # @api.multi
    def invoice_validate(self):
        for invoice in self.filtered(lambda invoice: invoice.partner_id not in invoice.message_partner_ids):
            invoice.message_subscribe([invoice.partner_id.id])
#         self._check_duplicate_supplier_reference()

        if self.move_id:

            if self.nro_factura:
                # self.name = self.nro_factura
                self.number = self.nro_factura

                self.payment_reference = self.nro_factura
                self.move_id.name = self.nro_factura
                self.move_id.ref = self.name
                for line in self.move_id.line_ids:
                    line.ref = self.name

        return self.write({'state': 'open'})

    @api.depends('tipo_comprobante','tipo_factura')
    def cod_tal(self):
        self.tipo_talonario = 0
        tipo= self.env.context.get('default_move_type')
        if not tipo:
            tipo = self.env.context.get('move_type')
        if not tipo:
            tipo=self.move_type
        if tipo in ('out_refund','in_refund'):
            self.tipo_comprobante=self.env.ref('paraguay_backoffice.tipo_comprobante_3')
            self.codigo_hechauka=self.tipo_comprobante.codigo_hechauka
        if self.tipo_comprobante:
            if self.tipo_comprobante.codigo_hechauka ==  3:
                self.tipo_talonario=4
                if tipo=='in_invoice':
                    self.tipo_talonario = None
                    self.tipo_comprobante = None
                    self.codigo_hechauka = None
                    raise ValidationError('No se puede seleccionar el tipo de Documento Nota de Credito en el Menú de Facturas. Favor crear el documento desde el menú Facturas Rectificativas/Notas de Credito ')


                elif tipo =='out_invoice':
                    self.tipo_comprobante = None
                    self.tipo_talonario = None
                    self.codigo_hechauka = None
                    raise ValidationError(
                        'No se puede seleccionar el tipo de Documento Nota de Credito en el Menú de Facturas. Favor crear el documento desde el menú Facturas Rectificativas/Notas de Credito ')

                    # elf.move_type='out_refund'

            elif self.tipo_comprobante.codigo_hechauka == 5:
                self.tipo_talonario = 5
            elif self.tipo_comprobante.codigo_hechauka == 1:
                self.tipo_talonario = 1
                if tipo=='in_refund':
                    self.tipo_comprobante = None
                    self.codigo_hechauka = None
                    self.tipo_talonario = None
                    raise ValidationError('No se puede seleccionar el tipo de Documento Factura en el Menú de Facturas Rectificativas. Favor crear el documento desde el menú Facturas ')

                elif tipo =='out_refund':
                    self.tipo_comprobante = None
                    self.codigo_hechauka = None
                    self.tipo_talonario = None
                    raise ValidationError('No se puede seleccionar el tipo de Documento Factura en el Menú de Facturas Rectificativas. Favor crear el documento desde el menú Facturas ')
            else:
                self.tipo_talonario=1


    # @api.onchange('date_invoice')
    # def fecha_vencimiento(self):
    #     if self.date_invoice:
    #         fecha_fact = datetime.strptime(self.date_invoice, "%Y-%m-%d")
    #     if self.tipo_factura == 1:
    #         self.date_due = fecha_fact
    #     elif self.tipo_factura == 2:
    #         self.date_due = fecha_fact + timedelta(days=30)




    @api.onchange('tipo_factura')
    def canti_cuotas(self):
        # self.date_invoice = fields.Date.context_today(self)
        if self.tipo_factura == 2:
            self.cantidad_cuotas = 1
        elif self.tipo_factura == 1:
            self.date_due = self.date_invoice

    @api.onchange('suc')
    def cambio_suc(self):
        suc_s = self.suc
        if suc_s:
            cant_suc = len(suc_s)
            if cant_suc == 1:
                suc_final = '00' + suc_s
            elif cant_suc == 2:
                suc_final = '0' + suc_s
            elif cant_suc == 3:
                suc_final = suc_s

            self.suc = suc_final
            if self.nro and self.sec and self.suc:
                self.nro_factura = self.suc + '-' + self.sec + '-' + self.nro

    @api.onchange('sec')
    def cambio_sec(self):
        sec_final = self.sec
        sec_s = self.sec
        if sec_s:
            cant_sec = len(sec_s)
            if cant_sec == 1:
                sec_final = '00' + sec_s
            elif cant_sec == 2:
                sec_final = '0' + sec_s
            elif cant_sec == 3:
                sec_final = sec_s

            self.sec = sec_final
            if self.nro and self.sec and self.suc:
                self.nro_factura = self.suc + '-' + self.sec + '-' + self.nro

    @api.onchange('nro')
    def cambio_nro(self):
        if self.nro:
            nro_final = self.nro
            nro_s = self.nro
            if nro_s:
                cant_nro = len(nro_s)
                if cant_nro == 1:
                    nro_final = '000000' + nro_s
                elif cant_nro == 2:
                    nro_final = '00000' + nro_s
                elif cant_nro == 3:
                    nro_final = '0000' + nro_s
                elif cant_nro == 4:
                    nro_final = '000' + nro_s
                elif cant_nro == 5:
                    nro_final = '00' + nro_s
                elif cant_nro == 6:
                    nro_final = '0' + nro_s
                else:
                    nro_final = nro_s

                self.nro = nro_final
                if self.nro and self.sec and self.suc:
                    self.nro_factura = self.suc + '-' + self.sec + '-' + self.nro
                elif self.nro:
                    self.nro_factura = self.nro


    @api.onchange('partner_id','partner_no_despachante')
    @api.depends('partner_id','partner_no_despachante')
    def _compute_RUC(self):
        for invoice in self:
            if not invoice.partner_id:
                invoice.ruc_factura = None
            else:

                if invoice.partner_no_despachante:
                    ruc = invoice.partner_no_despachante.rucdv
                    if not ruc:
                        partners = self.env['res.partner'].search([('id','child_of',invoice.partner_no_despachante.id)])
                        if partners:
                            for part in partners:
                                ruc = part.parent_id.rucdv
                    if ruc:
                        invoice.ruc_factura = ruc
                    if invoice.partner_no_despachante.digitointer:
                        if invoice.move_type in ('in_invoice','in_refund'):
                            invoice.ruc_factura='99999901-0'
                        else:
                            if invoice.company_id.exportador:
                                invoice.ruc_factura='66666601-6'
                            else:
                                invoice.ruc_factura = '88888801-5'
                    if not invoice.ruc_factura:
                        invoice.ruc_factura = '44444401-7'
                elif invoice.partner_id:
                    ruc = invoice.partner_id.rucdv
                    if not ruc:
                        partners = self.env['res.partner'].search([('id','child_of',invoice.partner_id.id)])
                        if partners:
                            for part in partners:
                                ruc = part.parent_id.rucdv
                    if ruc:
                        invoice.ruc_factura = ruc
                    if invoice.partner_id.digitointer:
                        if invoice.move_type in ('in_invoice','in_refund'):
                            invoice.ruc_factura='99999901-0'
                        else:
                            if invoice.company_id.exportador:
                                invoice.ruc_factura='66666601-6'
                            else:
                                invoice.ruc_factura = '88888801-5'
                    if not invoice.ruc_factura:
                        invoice.ruc_factura = '44444401-7'
                    

class ruc_tipo_documento(models.Model):
    _name = 'ruc.tipo.documento'
    _order = 'codigo_hechauka asc'

    comentario = fields.Text('Comentarios adicionales')
    name = fields.Char(string="Tipo de documento",required=True)
    tipo = fields.Selection([('1', 'Compra'), ('2', 'Venta'), ('3', 'Ambos'), ('4', 'Otro')])
    diario = fields.Many2one('account.journal',string='Diario asociado')
    codigo_hechauka= fields.Integer (string="Codigo en el Hechauka",required=True)
    talonaraio= fields.Many2one('ruc.documentos.timbrados',string="Talonario")
    mostrar_libro_iva=fields.Boolean(string="Mostrar Libro IVA", default=False)

class anulacion_remi(models.Model):
    _name = "ruc.motivo.anulacion"

    name = fields.Char(string="Motivo de la Anulación", required=True)
    tipo = fields.Selection([('factura', 'Factura'), ('remision', 'Remision'), ('ambos', 'Ambos')], required=True)
    activo = fields.Boolean(string='Activo?')
    descripcion = fields.Text(string='Descripcion detallada del motivo')

class documentos_timbrados(models.Model):
    _name = "ruc.documentos.timbrados"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']



    name = fields.Char(string="Numero Timbrado", required=True, unique=True,size=8)
    nombre_documento = fields.Char(string="Descripcion del Documento",required=True)
    tipo_documento = fields.Selection([('1', 'Factura'), ('2', 'Remisiones'), ('3', 'Retencion'), ('4', 'Nota de Credito'),('5','Autofactura')],
                                      string="Tipo Documento",required=True)
    # nivel = fields.Selection([(1, 'Obra'), (2, 'Administrativo'), (3, 'Contable'), (4, 'Administrador'), (5, 'Ghost')],
    #                          string="nivel")
    suc = fields.Char(string='Suc', size=3,required=True)
    sec = fields.Char(string='Sec', size=3,required=True)
    nro_ini = fields.Integer(string='Nro Inicio', size=7,required=True)
    nro_actual = fields.Integer(string='Nro Actual', size=7,required=True,tracking=True)
    nro_fin = fields.Integer(string='Nro Final', size=7,required=True)
    fecha_inicio = fields.Date(string='Fecha Inicio de Validez',required=True)
    fecha_final = fields.Date(string='Fecha de Expiracion de Timbrado',required=True)
    activo = fields.Boolean(string='Activo?')
    ultimo_nro_utilizado = fields.Char (string="Ultimo numero utilizado")
    company_id=fields.Many2one('res.company' ,string='Compañia',default=lambda self: self.env.company)
    user_ids = fields.Many2many('res.users', 'usuarios_timbrados_rel', 'user_id', 'timbrado_id',string='Usuarios')
    invoice_ids = fields.One2many('account.move','talonario_factura',string="Facturas")
    nro_autorizacion_autoimpresor = fields.Char(string="Nro. Autorizacion Autoimpresor")
    journal_id = fields.Many2one('account.journal',string="Diario asociado")

    def _get_default_company(self):
        return self.env.company_id

    _sql_constraints = [
        ('documento_timbrado_uniq', 'unique(tipo_documento,suc,sec,nro_ini,nro_fin,fecha_inicio,fecha_final,company_id)',
         "Este documento ya se encuentra registrado en el sistema.")]


    @api.onchange('suc')
    def cambio_suc(self):
        suc_s = self.suc
        if suc_s:
            cant_suc = len(suc_s)
            if cant_suc == 1:
                suc_final = '00' + suc_s
            elif cant_suc == 2:
                suc_final = '0' + suc_s
            elif cant_suc == 3:
                suc_final = suc_s

            self.suc = suc_final


    @api.onchange('sec')
    def cambio_sec(self):
        sec_final = self.sec
        sec_s = self.sec
        if sec_s:
            cant_sec = len(sec_s)
            if cant_sec == 1:
                sec_final = '00' + sec_s
            elif cant_sec == 2:
                sec_final = '0' + sec_s
            elif cant_sec == 3:
                sec_final = sec_s

            self.sec = sec_final




    @api.constrains('activo')
    def esta_activo(self):
     activo=self.activo

     if activo:
        talo = self.env['ruc.documentos.timbrados'].search([('company_id', '=', self.env.company.id), ('tipo_documento', '=', self.tipo_documento),('name', '=', self.name), ('activo', '=', True), ('suc', '=', self.suc), ('sec', '=', self.sec)])
        if talo:
            for talos in talo:
                if talos.id != self.id:
                    raise ValidationError('No se pueden tener dos documentos del mismo tipo activos en el sistema')


    # @api.multi
    def name_get(self):
    
        result = []
        for inv in self:
            result.append((inv.id, "%s - %s" % (inv.name, inv.nombre_documento )))
        return result
    
    @api.constrains('nro_ini')
    def numero_inicio(self):
        if self.nro_ini:
            if self.nro_fin:
                if self.nro_ini> self.nro_fin:
                    raise ValidationError ('Numero de inicio debe ser menor al numero final')
            else:
                raise ValidationError ('Debe haber un numero de finalizacion de timbrado')
        else:
            raise ValidationError ('Debe haber un numero de inicio')
    @api.constrains('nro_fin')
    def numero_final(self):
        if self.nro_fin:
            if self.nro_fin < self.nro_ini:
                raise ValidationError ('Numero Final debe ser mayor al numero de inicio')
        else:
            raise ValidationError ('Debe haber un numero de finalizacion de timbrado')


    @api.constrains('nro_actual')
    def numero_actual(self):
        if self.nro_actual:
            if self.nro_actual < self.nro_ini:
                raise ValidationError ('Numero actual debe ser mayor o igual que numero de inicio')
            elif self.nro_actual > (self.nro_fin+1):
                raise ValidationError ('Numero actual debe ser menor o igual que numero final')

    @api.onchange('activo','fecha_inicio','fecha_final')
    def _verificar_Fecha_carga(self):
       if self.fecha_inicio and self.fecha_final:
           d1 = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
           # fecha = datetime.strftime(fechas, "%Y/%m/%d")
           # d1 = datetime.strptime(str(datetime.now().date()), fmt)

           d2 = datetime.strptime(str(self.fecha_final), '%Y-%m-%d')
           d3 = datetime.strptime(str(self.fecha_inicio), '%Y-%m-%d')
           daysDiff = (d2 - d1).days

           dias_anti = (d3 - d1).days

           dias_entre = (d2 - d3).days

           if dias_entre < 0:
               raise ValidationError ('Fecha de Expiracion de Timbrado debe ser mayor a la fecha de Inicio')
