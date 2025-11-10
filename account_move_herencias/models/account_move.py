# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def default_get(self, fields_list):
        """Establecer valores por defecto"""
        res = super(AccountMove, self).default_get(fields_list)
        
        # Default tipo_comprobante: traer el que tiene codigo_hechauka == 1
        if 'tipo_comprobante' in fields_list and not res.get('tipo_comprobante'):
            tipo_comprobante = self.env['ruc.tipo.documento'].search([
                ('codigo_hechauka', '=', 1)
            ], limit=1)
            if tipo_comprobante:
                res['tipo_comprobante'] = tipo_comprobante.id
        
        # Default tipo_factura: '1' (Contado)
        if 'tipo_factura' in fields_list and not res.get('tipo_factura'):
            res['tipo_factura'] = '1'
        
        # Default cantidad_cuotas: 0 cuando es contado
        if 'cantidad_cuotas' in fields_list and not res.get('cantidad_cuotas'):
            if res.get('tipo_factura') == '1':
                res['cantidad_cuotas'] = 0
        
        return res

    @api.model
    def create(self, vals):
        """Al crear, establecer valores automáticos"""
        # Auto-configurar journal_id según move_type si no está definido
        if not vals.get('journal_id') and vals.get('move_type'):
            move_type = vals['move_type']
            journal_type = None
            if move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                journal_type = 'sale'
            elif move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                journal_type = 'purchase'
            
            if journal_type:
                journal = self.env['account.journal'].search([
                    ('type', '=', journal_type),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if journal:
                    vals['journal_id'] = journal.id
        
        # Auto-configurar currency_id según move_type y ámbito
        if not vals.get('currency_id') and vals.get('move_type'):
            move_type = vals['move_type']
            if move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                # Para compras: USD COMPRA (ambito == 'compra')
                currency = self.env['res.currency'].search([
                    ('ambito', '=', 'compra'),
                    ('name', '=', 'USD')
                ], limit=1)
                if currency:
                    vals['currency_id'] = currency.id
        
        # Auto-configurar tipo_comprobante si no está definido
        if not vals.get('tipo_comprobante'):
            tipo_comprobante = self.env['ruc.tipo.documento'].search([
                ('codigo_hechauka', '=', 1)
            ], limit=1)
            if tipo_comprobante:
                vals['tipo_comprobante'] = tipo_comprobante.id
        
        # Auto-configurar tipo_factura si no está definido
        if not vals.get('tipo_factura'):
            vals['tipo_factura'] = '1'
            vals['cantidad_cuotas'] = 0
        
        # Si es crédito, establecer cantidad_cuotas en 2 si no está definido
        if vals.get('tipo_factura') == '2' and not vals.get('cantidad_cuotas'):
            vals['cantidad_cuotas'] = 2
        
        # Configurar término de pago según tipo_factura
        if vals.get('tipo_factura'):
            if vals['tipo_factura'] == '1':
                # Inmediato para contado - buscar coincidencia exacta primero
                payment_term = self.env['account.payment.term'].search([
                    ('name', '=', 'Inmediato')
                ], limit=1)
                if not payment_term:
                    # Si no existe, buscar con ilike
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', 'Inmediato')
                    ], limit=1)
                if payment_term:
                    vals['invoice_payment_term_id'] = payment_term.id
            elif vals['tipo_factura'] == '2':
                # 30 días para crédito - buscar coincidencia exacta primero
                payment_term = self.env['account.payment.term'].search([
                    ('name', '=', '30 días')
                ], limit=1)
                if not payment_term:
                    # Buscar "30 días" con ilike
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', '30 días')
                    ], limit=1)
                if not payment_term:
                    # Como última opción, buscar solo "30" pero que contenga "día"
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', '30'),
                        ('name', 'ilike', 'día')
                    ], limit=1)
                if payment_term:
                    vals['invoice_payment_term_id'] = payment_term.id
        
        # Sincronizar fecha contable con fecha factura
        if vals.get('invoice_date') and not vals.get('date'):
            vals['date'] = vals['invoice_date']
        
        # Sincronizar fecha de vencimiento con fecha factura
        if vals.get('invoice_date') and not vals.get('invoice_date_due'):
            vals['invoice_date_due'] = vals['invoice_date']
        
        return super(AccountMove, self).create(vals)

    def write(self, vals):
        """Al escribir, actualizar valores relacionados"""
        # Si cambia tipo_factura a contado, resetear cantidad_cuotas
        if 'tipo_factura' in vals:
            if vals['tipo_factura'] == '1':
                vals['cantidad_cuotas'] = 0
                # Cambiar término de pago a Inmediato
                payment_term = self.env['account.payment.term'].search([
                    ('name', '=', 'Inmediato')
                ], limit=1)
                if not payment_term:
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', 'Inmediato')
                    ], limit=1)
                if payment_term:
                    vals['invoice_payment_term_id'] = payment_term.id
            elif vals['tipo_factura'] == '2':
                # Si cambia a crédito, establecer cantidad_cuotas en 2 si no está definido
                if 'cantidad_cuotas' not in vals:
                    vals['cantidad_cuotas'] = 2
                # Cambiar término de pago a 30 días
                payment_term = self.env['account.payment.term'].search([
                    ('name', '=', '30 días')
                ], limit=1)
                if not payment_term:
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', '30 días')
                    ], limit=1)
                if not payment_term:
                    payment_term = self.env['account.payment.term'].search([
                        ('name', 'ilike', '30'),
                        ('name', 'ilike', 'día')
                    ], limit=1)
                if payment_term:
                    vals['invoice_payment_term_id'] = payment_term.id
        
        # Sincronizar fecha contable con fecha factura
        if 'invoice_date' in vals:
            vals['date'] = vals['invoice_date']
            # También actualizar fecha de vencimiento si no está en vals
            if 'invoice_date_due' not in vals:
                vals['invoice_date_due'] = vals['invoice_date']
        
        # Auto-configurar journal_id si no está definido y hay move_type
        # Solo si es un registro único o si move_type está en vals
        if not vals.get('journal_id'):
            move_type = vals.get('move_type')
            if not move_type and len(self) == 1:
                # Solo acceder a self.move_type si es un singleton
                move_type = self.move_type
            
            if move_type:
                journal_type = None
                if move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                    journal_type = 'sale'
                elif move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                    journal_type = 'purchase'
                
                if journal_type:
                    journal = self.env['account.journal'].search([
                        ('type', '=', journal_type),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    if journal:
                        vals['journal_id'] = journal.id
        
        # Auto-configurar currency_id para compras si no está definido
        # Solo si es un registro único o si move_type está en vals
        move_type = vals.get('move_type')
        if not move_type and len(self) == 1:
            # Solo acceder a self.move_type si es un singleton
            move_type = self.move_type
        
        if move_type and move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            if 'currency_id' not in vals or not vals.get('currency_id'):
                currency = self.env['res.currency'].search([
                    ('ambito', '=', 'compra'),
                    ('name', '=', 'USD')
                ], limit=1)
                if currency:
                    vals['currency_id'] = currency.id
        
        return super(AccountMove, self).write(vals)

    @api.onchange('tipo_factura')
    def _onchange_tipo_factura(self):
        """Manejar cambios en tipo_factura"""
        if self.tipo_factura == '1':
            # Contado: resetear cantidad_cuotas a 0
            self.cantidad_cuotas = 0
            # Cambiar término de pago a Inmediato
            payment_term = self.env['account.payment.term'].search([
                ('name', '=', 'Inmediato')
            ], limit=1)
            if not payment_term:
                payment_term = self.env['account.payment.term'].search([
                    ('name', 'ilike', 'Inmediato')
                ], limit=1)
            if payment_term:
                self.invoice_payment_term_id = payment_term.id
            # Actualizar fecha de vencimiento a fecha factura
            if self.invoice_date:
                self.invoice_date_due = self.invoice_date
        elif self.tipo_factura == '2':
            # Crédito: establecer cantidad_cuotas en 2
            self.cantidad_cuotas = 2
            # Cambiar término de pago a 30 días
            payment_term = self.env['account.payment.term'].search([
                ('name', '=', '30 días')
            ], limit=1)
            if not payment_term:
                payment_term = self.env['account.payment.term'].search([
                    ('name', 'ilike', '30 días')
                ], limit=1)
            if not payment_term:
                payment_term = self.env['account.payment.term'].search([
                    ('name', 'ilike', '30'),
                    ('name', 'ilike', 'día')
                ], limit=1)
            if payment_term:
                self.invoice_payment_term_id = payment_term.id

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        """Sincronizar fecha contable y fecha de vencimiento con fecha factura"""
        if self.invoice_date:
            self.date = self.invoice_date
            # Solo actualizar fecha de vencimiento si no hay término de pago definido
            # o si el término de pago es Inmediato
            if not self.invoice_payment_term_id or \
               (self.invoice_payment_term_id and 'Inmediato' in self.invoice_payment_term_id.name):
                self.invoice_date_due = self.invoice_date

    @api.constrains('cantidad_cuotas', 'tipo_factura')
    def _check_cantidad_cuotas(self):
        """Validar que cantidad_cuotas no sea 0 cuando tipo_factura es crédito"""
        for rec in self:
            if rec.tipo_factura == '2' and rec.cantidad_cuotas == 0:
                raise ValidationError(
                    'No se puede guardar una factura a crédito con cantidad de cuotas igual a 0. '
                    'Debe especificar al menos una cuota.'
                )

    @api.onchange('move_type')
    def _onchange_move_type_currency(self):
        """Configurar currency_id según move_type"""
        if self.move_type:
            if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                # Para compras: auto-configurar USD COMPRA
                currency = self.env['res.currency'].search([
                    ('ambito', '=', 'compra'),
                    ('name', '=', 'USD')
                ], limit=1)
                if currency:
                    self.currency_id = currency.id
                # Retornar dominio para filtrar opciones
                return {
                    'domain': {
                        'currency_id': [
                            '|',
                            ('ambito', '=', 'compra'),
                            ('ambito', '=', False)
                        ]
                    }
                }
            elif self.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                # Para ventas: buscar USD VENTA si existe
                currency = self.env['res.currency'].search([
                    ('ambito', '=', 'venta'),
                    ('name', '=', 'USD')
                ], limit=1)
                # Si no existe, mantener la actual o usar moneda de compañía
                if not currency and not self.currency_id:
                    self.currency_id = self.env.company.currency_id
                # Retornar dominio para filtrar opciones
                return {
                    'domain': {
                        'currency_id': [
                            '|',
                            ('ambito', '=', 'venta'),
                            ('ambito', '=', False)
                        ]
                    }
                }
        return {}

    @api.constrains('currency_id', 'move_type')
    def _check_currency_ambito(self):
        """Validar que currency_id tenga el ámbito correcto según move_type"""
        for rec in self:
            if rec.currency_id and rec.move_type:
                if rec.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                    # Para compras: debe ser ámbito compra o no tener ámbito
                    if rec.currency_id.ambito and rec.currency_id.ambito != 'compra':
                        raise ValidationError(
                            'Para facturas de compra, la moneda debe tener ámbito "Compra".'
                        )
                elif rec.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                    # Para ventas: debe ser ámbito venta si tiene ámbito definido, o no tener ámbito
                    if rec.currency_id.ambito and rec.currency_id.ambito != 'venta':
                        raise ValidationError(
                            'Para facturas de venta, la moneda debe tener ámbito "Venta".'
                        )

