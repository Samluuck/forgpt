# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError



class Partner(models.Model):
    _inherit = 'account.move'

    vencimiento_timbrado = fields.Date(string="Vencimiento de timbrado",default=False)
    digitointer = fields.Char(related='partner_id.digitointer')
    libro_iva = fields.Boolean(string="Libro iva?")
    partner_no_despachante = fields.Many2one('res.partner', string='Emisor Factura')
    talonario_factura = fields.Many2one('ruc.documentos.timbrados', string="Talonario",domain=[('tipo_documento', 'in', ('1','4','5'))])
    valido_desde = fields.Date(related='talonario_factura.fecha_inicio', string="Valido desde")
    valido_hasta = fields.Date(related='talonario_factura.fecha_final', string="Valido hasta")
    bandera = fields.Boolean(default=False)
    aplicar_descuento = fields.Boolean(string="Aplicar descuento global",default=False)
    porcentaje_descuento = fields.Float(string="% Desc. global",default=0)
    producto_descuento = fields.Many2one('product.product',string="Producto de descuento")
    tipo_cambio_manual = fields.Float(string="Tipo de cambio manual",tracking=True)
    termino_pago = fields.Many2one(related="partner_id.property_payment_term_id", string="Termino de pago")
    termino_pago_proveedor = fields.Many2one(related="partner_id.property_supplier_payment_term_id",
                                             string="Termino de pago Proveedor")
    retiene_iva_cliente = fields.Boolean(string='Retiene IVA Cliente', related='partner_id.retiene_iva_cliente',
                                         store=False)
    tipo_cambio = fields.Float(string="Tipo Cambio", compute="_get_tipo_cambio")
    
    @api.depends('state', 'currency_id')
    def _get_tipo_cambio(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.id in (2, 168):
                tasa = rec.env['res.currency.rate'].search(
                    [
                        ('currency_id', '=', rec.currency_id.id),
                        ('name', '=', rec.invoice_date)
                    ],
                    order='name desc, id desc',
                    limit=1
                )
                rec.tipo_cambio = tasa.set_venta if tasa else 0
            else:
                rec.tipo_cambio = 0


    @api.depends('partner_id.retiene_iva_cliente')
    def _compute_retiene_iva_cliente(self):
        for move in self:
            move.retiene_iva_cliente = move.partner_id.retiene_iva_cliente
    @api.onchange('aplicar_descuento')
    def set_descuento(self):
        if not self.aplicar_descuento:
            self.porcentaje_descuento=0
            self.producto_descuento=None

    def aplicar_tipo_cambio_manual(self):
        for rec in self:
            for line in rec.line_ids:
                if line.debit > 0:
                    line.debit = abs(line.amount_currency * rec.tipo_cambio_manual)
                if line.credit > 0:
                    line.credit = abs(line.amount_currency * rec.tipo_cambio_manual)

    def aplicar_descuento_lineas(self):
        for rec in self:
            if rec.porcentaje_descuento > 0:
                if not rec.producto_descuento:
                    raise ValidationError('Favor seleccionar producto de descuento')
                account_move_line_obj = self.env['account.move.line']
                if len(rec.invoice_line_ids) == 0:
                    raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                new_line_vals = {
                    'product_id': rec.producto_descuento.id,
                    'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                    'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
                    'quantity': 1,
                    'product_uom_id': rec.producto_descuento.uom_id.id,
                    'price_unit': -sum(
                        (line.price_total * rec.porcentaje_descuento) / 100 for line in rec.invoice_line_ids),
                    'exclude_from_invoice_tab': False,
                    'move_id': rec.id,
                    'tiene_descuento' : True
                }
                rec.write({'invoice_line_ids': [(0, 0, new_line_vals)]})

                for line in rec.invoice_line_ids:
                    line._onchange_price_subtotal()
                    rec._recompute_dynamic_lines()

    @api.depends('partner_id.category_id')
    def _get_categ_clientes(self):
        for rec in self:
            string = ","
            if rec.partner_id.parent_id:
                rec.categoria_cliente = string.join(rec.partner_id.parent_id.mapped('category_id.name'))
            else:
                rec.categoria_cliente = string.join(rec.partner_id.mapped('category_id.name'))

    @api.depends('invoice_line_ids.product_id')
    def _get_productos(self):
        for rec in self:
            string = ","
            rec.productos_factura = string.join(rec.invoice_line_ids.mapped('product_id.name'))
            rec.categorias_productos_factura = string.join(rec.invoice_line_ids.mapped('product_id.categ_id.name'))

    @api.depends('partner_id')
    def _calc_cliente_rete(self):
        for rec in self:
            if rec.partner_id.retiene_iva_cliente:
                rec.factura_cliente_rete = True
            else:
                rec.factura_cliente_rete = False

    @api.onchange('tipo_comprobante')
    def _set_tipo_comprobante(self):
        if self.tipo_comprobante.diario:
            self.journal_id=self.tipo_comprobante.diario
        # if self.move_type == 'out_invoice':
        #     if self.tipo_comprobante.codigo_hechauka==1:
        #         if self.termino_pago:
        #             if 'Contado' in self.termino_pago.name or 'contado' in self.termino_pago.name:
        #                 self.tipo_factura='1'
        #             else:
        #                 self.tipo_factura='2'
        # elif self.move_type == 'in_invoice':
        #     if self.tipo_comprobante.codigo_hechauka==1:
        #         if self.termino_pago_proveedor:
        #             if 'Contado' in self.termino_pago_proveedor.name or 'contado' in self.termino_pago_proveedor.name:
        #                 self.tipo_factura='1'
        #             else:
        #                 self.tipo_factura='2'

    @api.constrains('nro_factura')
    def _check_nro_factura(self):
        facturas = None
        if self.nro_factura:
            if self.move_type == 'out_invoice' or self.move_type == 'out_refund':
                facturas = self.env['account.move'].search(
                    [['move_type', '=', self.move_type],['timbrado','=',self.timbrado],  ['company_id', '=', self.company_id.id],
                     ['nro_factura', '=', self.nro_factura]])
                if self.talonario_factura:
                    if self.nro:
                        if int(self.nro) > self.talonario_factura.nro_fin or int(self.nro) < self.talonario_factura.nro_ini:
                            raise ValidationError('El numero de factura esta fuera de rango de su talonario favor verificar')
            if self.move_type == 'in_invoice' or self.move_type == 'in_refund':
                facturas = self.env['account.move'].search(
                    [['move_type', '=', self.move_type],['timbrado','=',self.timbrado], ['partner_id', '=', self.partner_id.id],
                     ['company_id', '=', self.company_id.id], ['nro_factura', '=', self.nro_factura],['tipo_comprobante.codigo_rg90','in',(109,110,111,101)]])

            if facturas:
                for fact in facturas:
                    if fact.id != self.id:
                        raise exceptions.ValidationError(
                            'La factura %s ya se encuentra cargada en el sistema. Verifique datos. ' % (fact.nro_factura))


    @api.onchange('termino_pago', 'date_invoice')
    def _onchange_payment_term_date_invoice_term(self):
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if self.termino_pago:
            pterm = self.termino_pago
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            self.date_due = max(line[0] for line in pterm_list)
        elif self.date_due and (date_invoice > self.date_due):
            self.date_due = date_invoice

    @api.onchange('termino_pago')
    def _cambiar_tipo_factura(self):
        if (self.termino_pago.name != 'Contado'):
            self.tipo_factura = 2
            self.cantidad_cuotas = 1
        else:
            self.tipo_factura = 1

    # @api.multi
    def action_post(self):
        for rec in self:
            if rec.move_type not in ('entry','in_receipt','out_receipt'):
                if not rec.invoice_date:
                    raise ValidationError('Favor registrar fecha de factura')
                if not rec.vencimiento_timbrado:
                    raise ValidationError('Favor registrar fecha de vencimiento de timbrado')
                if rec.codigo_hechauka in (1,3):
                    if not rec.tipo_factura:
                        raise ValidationError('Favor registrar tipo de factura')
                if rec.vencimiento_timbrado < rec.invoice_date:
                    raise ValidationError('El timbrado se encuentra vencido con respecto a la fecha de factura.')
                if rec.move_type == 'out_invoice':
                    if not rec.talonario_factura:
                        raise ValidationError ('Debe asignar un talonario a esta factura')
                if rec.currency_id.id != self.env.company.currency_id.id:
                    coti = self.env['res.currency.rate'].search(
                        [['name', '=', rec.invoice_date], ['currency_id', '=', rec.currency_id.id]])
                    if not coti:
                        raise ValidationError(
                            'No se encuentra cotizacion para el dia %s . Verifique que la cotizacion se encuentre cargada ' % rec.invoice_date)
            factura = super(Partner, rec).action_post()
            if rec.nro_factura:
                rec.name = rec.nro_factura
            return factura

    # @api.constrains('talonario_factura')
    @api.onchange('talonario_factura')
    def remision(self):
        if self.talonario_factura:
            if self.talonario_factura.journal_id:
                self.journal_id = self.talonario_factura.journal_id
            self.timbrado = self.talonario_factura.name
            suc = self.talonario_factura.suc
            sec = self.talonario_factura.sec
            nro = self.get_next_nro(self.talonario_factura)
            self.suc = suc
            self.sec = sec
            nro_final = self.agregar_ceros(nro)
            self.nro = nro_final
            self.nro_factura = str(suc) + '-' + str(sec) + '-' + str(nro_final)
            self.vencimiento_timbrado=self.talonario_factura.fecha_final

    @api.onchange('partner_id','tipo_comprobante')
    def _setTimbrado(self):
        for invoice in self:
            if invoice.partner_id.supplier:
                if invoice.partner_no_despachante:
                    if invoice.partner_no_despachante.timbrado:
                         invoice.timbrado = invoice.partner_id_no_despachante.timbrado
                         invoice.vencimiento_timbrado = invoice.partner_no_despachante.vencimiento_timbrado
                elif invoice.partner_id.timbrado and invoice.move_type=='in_invoice':
                    invoice.timbrado = invoice.partner_id.timbrado
                    invoice.vencimiento_timbrado = invoice.partner_id.vencimiento_timbrado
            if invoice.move_type == 'out_invoice':
                if self.env.user.documento_factura:
                    invoice.talonario_factura = self.env.user.default_documento_factura
                    if self.env.user.default_documento_factura:
                        if self.env.user.default_documento_factura.journal_id:
                            invoice.journal_id = self.env.user.default_documento_factura.journal_id
                    if invoice.talonario_factura:
                        invoice.timbrado = invoice.talonario_factura.name
                        invoice.vencimiento_timbrado = invoice.talonario_factura.fecha_final
                        invoice.suc = invoice.talonario_factura.suc
                        invoice.sec = invoice.talonario_factura.sec
                        invoice.nro = invoice.talonario_factura.nro_actual
                        invoice.cambio_nro()

    def agregar_ceros(self,nro):
        nro_s = str(nro)
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
        return nro_final
    def get_next_nro(self,talonario_factura):
        nro_s = str(talonario_factura.nro_actual)
        nro_final = self.agregar_ceros(nro_s)
        next_invoice = self.env['account.move'].search_count([('talonario_factura', '=',talonario_factura.id),
                                                              ('nro', '=', nro_final)])
        nro_actual = talonario_factura.nro_actual
        if next_invoice > 0:
            nro_actual = talonario_factura.nro_actual + 1
            bandera = False
            while not bandera:
                next_invoice = self.env['account.move'].search_count(
                    [('talonario_factura', '=', talonario_factura.id), ('nro', '=', self.agregar_ceros(nro_actual))])
                if next_invoice > 0:
                    nro_actual = nro_actual + 1
                else:
                    bandera = True
        return nro_actual


    def quitar_ceros(self,nro):
        return nro.lstrip("0")
    @api.model
    def create(self, vals):
        if vals:
            invoice = super(Partner, self).create(vals)
            if invoice.move_type in ('out_invoice', 'out_refund'):
                if vals.get('nro_factura'):
                    if vals.get('nro'):
                        nro = self.quitar_ceros(vals.get('nro'))
                    else:
                        try:
                            numero_final = vals.get('nro_factura').split("-")[2]
                            nro = self.quitar_ceros(numero_final)
                        except:
                            raise ValidationError('Favor registrar nro. de factura')
                    if int(nro) == invoice.talonario_factura.nro_actual:
                        invoice.talonario_factura.write({'ultimo_nro_utilizado': vals.get('nro_factura'),
                                                  'nro_actual': invoice.talonario_factura.nro_actual + 1})
                    elif int(nro) > invoice.talonario_factura.nro_actual:
                        raise ValidationError('No se puede utilizar un número mayor al número actual del talonario: %s' % (invoice.talonario_factura.nro_actual))
            return invoice

    # @api.multi
    def write(self, vals):
        for move in self:
            if len(move)>1:
                nro = None
            else:
                nro= move.nro_factura
            rec = super(Partner, move).write(vals)
            if len(move)> 1:
                asd=0
                # return rec
            else:
                if move.move_type in ('out_invoice', 'out_refund'):
                    if vals.get('nro_factura'):
                        if vals.get('nro'):
                            nro = self.quitar_ceros(vals.get('nro'))
                        else:
                            try:
                                numero_final = vals.get('nro_factura').split("-")[2]
                                nro = self.quitar_ceros(numero_final)
                            except:
                                raise ValidationError('Favor registrar nro. de factura')

                        if int(nro) == move.talonario_factura.nro_actual:
                            move.talonario_factura.write({'ultimo_nro_utilizado': vals.get('nro_factura'),
                                                             'nro_actual': move.talonario_factura.nro_actual + 1})
                        elif int(nro) > move.talonario_factura.nro_actual:
                            raise ValidationError(
                                'No se puede utilizar un número mayor al número actual del talonario: %s' % (
                                    move.talonario_factura.nro_actual))



