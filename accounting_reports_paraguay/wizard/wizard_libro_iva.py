# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api

import time, collections
import io
from odoo.exceptions import ValidationError
import xlsxwriter

from datetime import date

import base64
import xlwt
import base64
import xlsxwriter
from io import StringIO
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition

import werkzeug
import logging

_logger = logging.getLogger(__name__)


class WizardReportLibroIVACompra(models.TransientModel):
    _name = "libro_iva_paraguay.wizard.libro_iva"

    tipo = fields.Selection([('compra', 'Compra'), ('venta', 'Venta')], string="Tipo de Libro IVA")
    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    borrador = fields.Boolean(string="Incluir facturas en Borrador")
    cancelado = fields.Boolean(string="Incluir facturas anuladas")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())
    usuario_id = fields.Many2one('res.users', string='Usuario')
    tipo_archivo = fields.Selection([('pdf', 'PDF'), ('xlsx', 'XLSX')], string="Exportar Como", default='pdf')
    cuenta_analitica_id = fields.Many2one('account.analytic.account')
    tipo_iva = fields.Many2one('account.tipo.iva', string="Tipo de IVA",
                               help='Si se deja este campo vacio trae todas las facturas')
    cruzado = fields.Boolean(string="Documentos Cruzados",
                             help="En caso de estar marcado este campo al Generar el Libro Compra aparecerán las Facturas de Compra y Nota de Credito a clientes. En caso de que el informe sea Libro Ventas, en el mismo apareceran las Facturas de Cliente y Nota de Credito de Proveedor ")
    mostrar_numeracion = fields.Boolean(string="Para rúbrica?", defaul=False)

    def _get_default_company(self):
        return self.env.company.id

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin', 'tipo', 'usuario_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin', 'tipo', 'usuario_id'])[0])
        if self.tipo_archivo == 'pdf':
            return self.env.ref('accounting_reports_paraguay.report_libro_iva_id').report_action(self, data)
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/getLibroIva/' + str(self.id),
                'target': 'current'
            }

    def get_datos_libro_iva(self, fecha_inicio, fecha_fin, tipo, borrador, usuario_id, company_id, cancelado):

        """
        La funcion debe recibir como parametros:

            - Fecha Inicio: Fecha inicial para generar los datos
            - Fecha Fin:    Fecha final para generar los datos
            - Tipo: Puede ser 'compra' o 'venta'

        :return: Una lista con:
            - Un diccionario python que tiene como llave ('key') a la factura
                y como argumento del diccionario una lista que posee los montos relacionados a esta factura
                Ejemplo:
                        Formato del Diccionario -> ([(factura,[ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ])])

                        ([(account.invoice, [10000,1000,0,0,0])])
            - Sumatoria de los montos de los impuestos  de las facturas -> [ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ]
            - Sumatoria de los montos de los impuestos de las notas de credito -> [ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ]


        """
        _logger.info('***********************************************')

        iva10 = self.env.ref('l10n_py.grupo_10')
        iva5 = self.env.ref('l10n_py.grupo_5')
        exentas = self.env.ref('l10n_py.grupo_exenta')
        tipo_factura = self.env.ref('paraguay_backoffice.tipo_comprobante_1').id
        tipo_nc = self.env.ref('paraguay_backoffice.tipo_comprobante_3').id
        tipo_despacho = self.env.ref('paraguay_backoffice.tipo_comprobante_4').id
        tipo_autofactura = self.env.ref('paraguay_backoffice.tipo_comprobante_5').id
        tipos_documento = self.env['ruc.tipo.documento'].search([('mostrar_libro_iva', '=', True)])

        # Variables,  Listas y Diccionario a ser utilizados
        lista_totales = []
        nc_totales = []
        impuestos = []
        impuestos_nc = []
        monto_iva10 = 0.0
        monto_gravada10 = 0.0
        monto_iva5 = 0.0
        monto_gravada5 = 0.0
        monto_exentas = 0.0
        total_iva10 = total_iva10s = total_iva5 = total_iva5s = total_grav10 = total_grav5 = total_exentas = 0.0
        nc_total_iva10 = nc_total_iva5 = nc_total_grav10 = nc_total_grav5 = nc_total_exentas = 0.0
        diccionario_facturas = collections.OrderedDict()
        diccionario_nc = collections.OrderedDict()
        domain = []
        # domain += [('company_id', '=', company_id.id), ('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)]
        # domain += [('company_id', '=', company_id.id),('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin),('no_mostrar_libro_iva','=',False),('tipo_comprobante','in',(tipo_factura,tipo_nc,tipo_despacho,tipo_autofactura))]
        domain += [('company_id', '=', company_id.id), ('invoice_date', '>=', fecha_inicio),
                   ('invoice_date', '<=', fecha_fin), ('no_mostrar_libro_iva', '=', False),
                   ('tipo_comprobante', 'in', (tipos_documento.ids))]
        if usuario_id:
            domain += [('user_id', '=', usuario_id.id)]
        if tipo == 'venta':
            if self.cruzado:
                domain += [('move_type', 'in', ('out_invoice', 'in_refund'))]
            else:
                domain += [('move_type', 'in', ('out_invoice', 'out_refund'))]
        else:
            _logger.warning('if tipo == compra')
            if self.cruzado:
                domain += [('move_type', 'in', ('in_invoice', 'out_refund'))]
            else:
                domain += [('move_type', 'in', ('in_invoice', 'in_refund'))]
        if self.tipo_iva:
            domain += [('tipo_iva_id', '=', self.tipo_iva.id)]
        if borrador and cancelado:
            domain += [('state', 'in', ('draft', 'posted', 'cancel'))]
        elif borrador and not cancelado:
            domain += [('state', 'in', ('posted', 'draft'))]
        elif not borrador and cancelado:
            domain += [('state', 'in', ('cancel', 'posted'))]
        else:
            domain += [('state', '=', 'posted')]

        # facturas = self.env['account.invoice'].search(domain, order='nro_factura')
        facturas = self.env['account.move'].search(domain, order='nro_factura')
        domain = []
        cuenta_analitica_id = None
        if tipo == 'venta':
            try:
                if cuenta_analitica_id:
                    facturas = facturas.filtered(
                        lambda r: r.invoice_line_ids.account_analytic_id == cuenta_analitica_id)

                factu = facturas.sorted(key=lambda r: (r.invoice_date,r.suc, r.sec, r.nro))
            except Exception as e:
                factu = facturas.sorted(key=lambda r: r.invoice_date)
        else:

            factu = facturas.sorted(key=lambda r: r.invoice_date)
        ban = 1
        for f in factu:
            if f.state != 'cancel':
                m = f
                for linea in m.line_ids:
                    if linea.tax_line_id:
                        if linea.move_id.id == 7727:
                            print('HOLA')
                            _logger.warning('HOLA')

                        if linea.tax_line_id.tax_group_id.id == iva10.id:
                            monto_iva10 += linea.balance
                            if f.tipo_comprobante.codigo_hechauka == 4:
                                monto_gravada10 += linea.balance * 0
                                total_grav10 += linea.balance * 0
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_iva10 += linea.balance
                                monto_nuevo_iva10 = linea.balance
                            else:
                                nc_total_iva10 += abs(linea.balance)

                            # total_iva10 += abs(linea.balance)
                        if linea.tax_line_id.tax_group_id.id == iva5.id:
                            monto_iva5 += abs(linea.balance)
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_iva5 += abs(linea.balance)
                            else:
                                nc_total_iva5 += abs(linea.balance)

                    else:
                        _logger.warning('GABRIEL CRAC')
                        if len(linea.tax_ids) == 1:
                            linea_tax = linea.tax_ids
                            # Si la factura posee iva 10%
                            if linea_tax.tax_group_id.id == iva10.id:

                                monto_gravada10 += linea.balance
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_grav10 += linea.balance
                                    _logger.warning('***********el monto de iva 10 es de **********', total_grav10)
                                else:
                                    nc_total_grav10 += linea.balance
                            # Si la factura posee iva 5%
                            if linea_tax.tax_group_id.id == iva5.id:
                                monto_gravada5 += linea.balance
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_grav5 += linea.balance
                                else:
                                    nc_total_grav5 += linea.balance
                            # Si la factura posee exentas%
                            if linea_tax.tax_group_id.id == exentas.id:
                                monto_exentas += linea.balance
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_exentas += linea.balance
                                else:
                                    nc_total_exentas += linea.balance
                        elif not linea.tax_ids and linea.account_id.internal_type not in ('payable', 'receivable'):
                            monto_exentas += linea.balance
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_exentas += linea.balance
                            else:
                                nc_total_exentas += linea.balance
                        else:
                            if not f.line_ids.mapped('tax_ids'):
                                monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0


            else:
                monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0
                _logger.warning(
                    '***** monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0  *****')
            # Lista de impuesto para una factura
            if f.move_type in ('in_refund', 'out_refund'):
                if monto_gravada10 > 0:
                    monto_10 = monto_iva10 + monto_gravada10
                    monto_nuevo_iva10 = round(monto_10 / 11)
                    monto_nuevo_gravada_10 = round(monto_10 / 1.1)
                else:
                    monto_nuevo_iva10 = monto_iva10
                    monto_nuevo_gravada_10 = monto_gravada10
                if monto_gravada5 > 0:
                    monto_5 = monto_iva5 + monto_gravada5
                    monto_nuevo_iva5 = round(monto_5 / 21)
                    monto_nuevo_gravada_5 = round(monto_5 / 2.1)
                else:
                    monto_nuevo_iva5 = monto_iva5
                    monto_nuevo_gravada_5 = monto_gravada5
                impuestos_nc.append(monto_nuevo_gravada_10)
                impuestos_nc.append(monto_nuevo_iva10)

                impuestos_nc.append(monto_nuevo_gravada_5)
                impuestos_nc.append(monto_nuevo_iva5)
                impuestos_nc.append(monto_exentas)
                # Diccionario donde el key es la NOTA DE CREDITOS anidadas a sus impuestos
                diccionario_nc.setdefault(f, impuestos_nc)
            else:
                if monto_gravada10 > 0:
                    monto_10 = monto_iva10 + monto_gravada10
                    # monto_nuevo_iva10=round(monto_10/11)
                    # monto_nuevo_iva10=round(monto_gravada10/10)
                    monto_nuevo_gravada_10 = round(monto_gravada10)

                else:
                    monto_nuevo_iva10 = monto_iva10

                    monto_nuevo_gravada_10 = monto_gravada10
                # total_iva10 += monto_nuevo_iva10
                if monto_gravada5 > 0:
                    monto_5 = monto_iva5 + monto_gravada5
                    monto_nuevo_iva5 = round(monto_5 / 21)
                    monto_nuevo_gravada_5 = round(monto_5 / 1.05)
                    print('iva 5')
                    print(monto_5)
                    print(monto_nuevo_gravada_5)
                    print(monto_nuevo_iva5)
                else:
                    monto_nuevo_iva5 = monto_iva5
                    monto_nuevo_gravada_5 = monto_gravada5
                # total_iva5 += monto_nuevo_iva5
                impuestos.append(abs(monto_nuevo_gravada_10))
                impuestos.append(abs(monto_nuevo_iva10))
                impuestos.append(abs(monto_nuevo_gravada_5))
                impuestos.append(abs(monto_nuevo_iva5))
                impuestos.append(abs(monto_exentas))

                # Diccionario donde el key es la Factura anidadas a sus impuestos
                diccionario_facturas.setdefault(f, impuestos)

            # Se resetea los valores para la siguiente Factura
            impuestos = []
            impuestos_nc = []
            monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_nuevo_iva10= monto_gravada10 = 0.0

        # Lista de totales de las facturas
        lista_totales.append(total_grav10)
        # lista_totales.append(total_iva10)
        lista_totales.append(total_grav10 / 10)
        lista_totales.append(total_grav5)
        lista_totales.append(total_iva5)
        lista_totales.append(total_exentas)

        # Lista de totales de las Notas de creditos
        nc_totales.append(nc_total_grav10)
        nc_totales.append(nc_total_iva10)
        nc_totales.append(nc_total_grav5)
        nc_totales.append(nc_total_iva5)
        nc_totales.append(nc_total_exentas)

        # Para poder iterar el dicionario Facturas con sus impuestos
        fac = diccionario_facturas.items()
        nc = diccionario_nc.items()

        list_return = []
        list_return.append(fac)
        list_return.append(lista_totales)
        list_return.append(nc_totales)
        list_return.append(nc)

        return list_return

    def agregar_punto_de_miles(self, numero, moneda):
        numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    def convertir_guaranies(self, factura):

        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.invoice_date)),
             ('company_id', '=', factura.company_id.id)])
        if not rate:
            rate = self.env['res.currency.rate'].search(
                [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.invoice_date)),
                 ('company_id', '=', None)])

        if len(rate) > 0:
            monto = round(factura.amount_total * (1 / rate.rate))
            monto = self.agregar_punto_de_miles(monto, 1)
            return monto
        else:
            raise ValidationError('No existe cotización en la fecha %s' % (factura.invoice_date))

    def convertir_guaranies_2(self, factura):
        # if factura.move_id:
        if factura:
            suma = sum([abs(round(l.debit)) for l in factura.line_ids if l.account_id == factura.account_id])
            valor = self.agregar_punto_de_miles(suma, 1)
            return valor
        else:
            raise ValidationError('No se encontro asiento de la factura %s' % factura.nro_factura)


class ReporteLibroCompras(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.libro_iva_paraguay_report'

    # @api.multi
    def _get_report_values(self, docids, data=None):

        docs = self.env['libro_iva_paraguay.wizard.libro_iva'].browse(self.env.context.get('active_id'))
        list_get_libro_iva = self.get_datos_libro_iva(docs.fecha_inicio, docs.fecha_fin, docs.tipo, docs.borrador,
                                                      docs.usuario_id, docs.company_id, docs.cuenta_analitica_id,
                                                      docs.tipo_iva, docs.cancelado)
        fac = list_get_libro_iva[0]
        lista_totales = list_get_libro_iva[1]
        nc_totales = list_get_libro_iva[2]
        nota_credito = list_get_libro_iva[3]

        docargs = {
            'doc_ids': self.ids,
            'doc_model': 'libro_iva_paraguay.wizard.libro_iva',
            'docs': docs,
            'time': time,
            'fac': fac,
            'lista_totales': lista_totales,
            'nc_totales': nc_totales,
            'nota_credito': nota_credito
        }
        return docargs

    def get_datos_libro_iva(self, fecha_inicio, fecha_fin, tipo, borrador, usuario_id, company_id, cuenta_analitica_id,
                            tipo_iva, cancelado):
        """
        La funcion debe recibir como parametros:

            - Fecha Inicio: Fecha inicial para generar los datos
            - Fecha Fin:    Fecha final para generar los datos
            - Tipo: Puede ser 'compra' o 'venta'

        :return: Una lista con:
            - Un diccionario python que tiene como llave ('key') a la factura
                y como argumento del diccionario una lista que posee los montos relacionados a esta factura
                Ejemplo:
                        Formato del Diccionario -> ([(factura,[ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ])])

                        ([(account.invoice, [10000,1000,0,0,0])])
            - Sumatoria de los montos de los impuestos  de las facturas -> [ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ]
            - Sumatoria de los montos de los impuestos de las notas de credito -> [ monto_gravada_10%, monto_iva10%, monto_gravada_5%, monto_iva5%, monto_exento ]


        """

        iva10 = self.env.ref('l10n_py.grupo_10')
        iva5 = self.env.ref('l10n_py.grupo_5')
        exentas = self.env.ref('l10n_py.grupo_exenta')
        tipo_factura = self.env.ref('paraguay_backoffice.tipo_comprobante_1').id
        tipo_nc = self.env.ref('paraguay_backoffice.tipo_comprobante_3').id
        tipo_despacho = self.env.ref('paraguay_backoffice.tipo_comprobante_4').id
        tipo_autofactura = self.env.ref('paraguay_backoffice.tipo_comprobante_5').id
        tipo_factura_exterior = self.env.ref('paraguay_backoffice.tipo_comprobante_8').id
        tipos_documento = self.env['ruc.tipo.documento'].search([('mostrar_libro_iva', '=', True)])

        # Variables,  Listas y Diccionario a ser utilizados
        lista_totales = []
        nc_totales = []
        impuestos = []
        impuestos_nc = []
        monto_iva10 = 0.0
        monto_gravada10 = 0.0
        monto_iva5 = 0.0
        monto_gravada5 = 0.0
        monto_exentas = 0.0
        total_iva10 = total_iva5 = total_grav10 = total_grav5 = total_exentas = 0.0
        nc_total_iva10 = nc_total_iva5 = nc_total_grav10 = nc_total_grav5 = nc_total_exentas = 0.0
        diccionario_facturas = collections.OrderedDict()
        diccionario_nc = collections.OrderedDict()
        docsa = self.env['libro_iva_paraguay.wizard.libro_iva'].browse(self.env.context.get('active_id'))

        domain = []
        # domain += [('company_id', '=', company_id.id), ('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)]
        # domain += [('company_id', '=', company_id.id), ('invoice_date', '>=', fecha_inicio),
        #            ('invoice_date', '<=', fecha_fin), ('no_mostrar_libro_iva', '=', False),
        #            ('tipo_comprobante', 'in', (tipo_factura, tipo_nc, tipo_despacho, tipo_autofactura,tipo_factura_exterior))]
        domain += [('company_id', '=', company_id.id), ('invoice_date', '>=', fecha_inicio),
                   ('invoice_date', '<=', fecha_fin), ('no_mostrar_libro_iva', '=', False),
                   ('tipo_comprobante', 'in', (tipos_documento.ids))]
        if usuario_id:
            domain += [('user_id', '=', usuario_id.id)]
        if tipo == 'venta':
            if docsa.cruzado:
                domain += [('move_type', 'in', ('out_invoice', 'in_refund'))]
            else:
                domain += [('move_type', 'in', ('out_invoice', 'out_refund'))]
        else:
            if docsa.cruzado:
                domain += [('move_type', 'in', ('in_invoice', 'out_refund'))]
            else:
                domain += [('move_type', 'in', ('in_invoice', 'in_refund'))]

        if tipo_iva:
            domain += [('tipo_iva_id', '=', tipo_iva.id)]
        if borrador and cancelado:
            domain += [('state', 'in', ('draft', 'posted', 'cancel'))]
        elif borrador and not cancelado:
            domain += [('state', 'in', ('posted', 'draft'))]
        elif not borrador and cancelado:
            domain += [('state', 'in', ('cancel', 'posted'))]
        else:
            domain += [('state', '=', 'posted')]
        # facturas = self.env['account.invoice'].search(domain, order='nro_factura')
        facturas = self.env['account.move'].search(domain, order='nro_factura')
        domain = []
        if tipo == 'venta':
            try:
                if cuenta_analitica_id:
                    facturas = facturas.filtered(lambda r: r.id in (list(
                        set([l.invoice_id.id for l in r.invoice_line_ids if
                             l.account_analytic_id == cuenta_analitica_id]))))

                factu = facturas.sorted(key=lambda r: (r.invoice_date, r.suc, r.sec, r.nro))
            except Exception as e:
                factu = facturas.sorted(key=lambda r: r.invoice_date)
        else:
            factu = facturas.sorted(key=lambda r: r.invoice_date)
        ban = 1
        for f in factu:

            # si la factura no esta cancelada se hacen los calculos
            if f.state != 'cancel':
                m = f
                for linea in m.line_ids:

                    if linea.tax_line_id:
                        if linea.tax_line_id.tax_group_id.id == iva10.id:
                            _logger.warning('if linea.tax_line_id.tax_group_id.id == iva10.id:')
                            monto_iva10 += abs(round(linea.balance, 0))
                            _logger.warning('****************** El monto del iva es:', monto_iva10)
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_iva10 += abs(round(linea.balance, 0))
                                _logger.warning('****************** El monto del iva es:', total_iva10)
                            else:
                                _logger.warning('**** ENTRA EN EL ELSE:')
                                nc_total_iva10 += abs(round(linea.balance, 0))
                        if linea.tax_line_id.tax_group_id.id == iva5.id:
                            monto_iva5 += abs(round(linea.balance, 0))
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_iva5 += abs(round(linea.balance, 0))
                            else:
                                nc_total_iva5 += abs(round(linea.balance, 0))
                    else:
                        if len(linea.tax_ids) == 1:
                            linea_tax = linea.tax_ids
                            # Si la factura posee iva 10%
                            if linea_tax.tax_group_id.id == iva10.id:
                                monto_gravada10 += round(linea.balance, 0)
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_grav10 += round(linea.balance, 0)
                                else:

                                    nc_total_grav10 += round(linea.balance, 0)
                                    # print(nc_total_grav10)
                            # Si la factura posee iva 5%
                            if linea_tax.tax_group_id.id == iva5.id:
                                monto_gravada5 += round(linea.balance, 0)
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_grav5 += round(linea.balance, 0)
                                else:
                                    nc_total_grav5 += round(linea.balance, 0)
                            # Si la factura posee exentas%
                            if linea_tax.tax_group_id.id == exentas.id:
                                monto_exentas += round(linea.balance, 0)
                                if f.move_type in ('out_invoice', 'in_invoice'):
                                    total_exentas += round(linea.balance, 0)
                                else:
                                    nc_total_exentas += round(linea.balance, 0)
                        elif not linea.tax_ids and linea.account_id.internal_type not in ('payable', 'receivable'):
                            monto_exentas += linea.balance
                            if f.move_type in ('out_invoice', 'in_invoice'):
                                total_exentas += linea.balance
                            else:
                                nc_total_exentas += linea.balance

                monto_gravada10 = abs(monto_gravada10)
                # total_grav10 = abs(total_grav10)
                # nc_total_grav10 = abs(nc_total_grav10)
                monto_gravada5 = abs(monto_gravada5)
                # total_grav5 = abs(total_grav5)
                # nc_total_grav5= abs(nc_total_grav5)
                monto_exentas = abs(monto_exentas)
                # total_exentas = abs(total_exentas)
                # nc_total_exentas = abs(nc_total_exentas)






            # si la factura esta cancelada
            else:
                monto_gravada10 = 0.0
                monto_iva10 = 0.0
                monto_gravada5 = 0.0
                monto_iva5 = 0.0
                monto_exentas = 0.0

            # Lista de impuesto para una factura
            if f.move_type in ('in_refund', 'out_refund'):
                if monto_gravada10 > 0:
                    monto_10 = monto_iva10 + monto_gravada10
                    monto_nuevo_iva10 = round(monto_10 / 11)
                    monto_nuevo_gravada_10 = round(monto_10 / 1.1)
                else:
                    monto_nuevo_iva10 = monto_iva10
                    monto_nuevo_gravada_10 = monto_gravada10
                if monto_gravada5 > 0:
                    monto_5 = monto_iva5 + monto_gravada5
                    monto_nuevo_iva5 = round(monto_5 / 21)
                    monto_nuevo_gravada_5 = round(monto_5 / 2.1)
                else:
                    monto_nuevo_iva5 = monto_iva5
                    monto_nuevo_gravada_5 = monto_gravada5
                impuestos_nc.append(monto_nuevo_gravada_10)
                impuestos_nc.append(monto_nuevo_iva10)

                impuestos_nc.append(monto_nuevo_gravada_5)
                impuestos_nc.append(monto_nuevo_iva5)
                impuestos_nc.append(monto_exentas)
                # Diccionario donde el key es la NOTA DE CREDITOS anidadas a sus impuestos
                diccionario_nc.setdefault(f, impuestos_nc)
            else:
                if monto_gravada10 > 0:
                    monto_10 = monto_iva10 + monto_gravada10
                    monto_nuevo_iva10 = round(monto_10 / 11)
                    monto_nuevo_gravada_10 = round(monto_10 / 1.1)
                else:
                    monto_nuevo_iva10 = monto_iva10
                    monto_nuevo_gravada_10 = monto_gravada10
                if monto_gravada5 > 0:
                    monto_5 = monto_iva5 + monto_gravada5
                    monto_nuevo_iva5 = round(monto_5 / 21)
                    monto_nuevo_gravada_5 = round(monto_5 / 1.05)
                    print('iva 5')
                    print(monto_5)
                    print(monto_nuevo_gravada_5)
                    print(monto_nuevo_iva5)
                else:
                    monto_nuevo_iva5 = monto_iva5
                    monto_nuevo_gravada_5 = monto_gravada5
                impuestos.append(monto_nuevo_gravada_10)
                impuestos.append(monto_nuevo_iva10)
                impuestos.append(monto_nuevo_gravada_5)
                impuestos.append(monto_nuevo_iva5)
                impuestos.append(monto_exentas)

                # Diccionario donde el key es la Factura anidadas a sus impuestos
                diccionario_facturas.setdefault(f, impuestos)

            # Se resetea los valores para la siguiente Factura
            impuestos = []
            impuestos_nc = []
            monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0

        total_grav10 = abs(total_grav10)
        nc_total_grav10 = abs(nc_total_grav10)
        total_grav5 = abs(total_grav5)
        nc_total_grav5 = abs(nc_total_grav5)
        total_exentas = abs(total_exentas)
        nc_total_exentas = abs(nc_total_exentas)
        # Lista de totales de las facturas
        lista_totales.append(total_grav10)
        lista_totales.append(total_iva10)
        lista_totales.append(total_grav5)
        lista_totales.append(total_iva5)
        lista_totales.append(total_exentas)

        # Lista de totales de las Notas de creditos
        nc_totales.append(nc_total_grav10)
        nc_totales.append(nc_total_iva10)
        nc_totales.append(nc_total_grav5)
        nc_totales.append(nc_total_iva5)
        nc_totales.append(nc_total_exentas)
        # print(nc_totales)
        # Para poder iterar el dicionario Facturas con sus impuestos
        fac = diccionario_facturas.items()
        nc = diccionario_nc.items()

        list_return = []
        list_return.append(fac)
        list_return.append(lista_totales)
        list_return.append(nc_totales)
        list_return.append(nc)

        return list_return


class DownloadXLS(http.Controller):
    @http.route('/getLibroIva/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['libro_iva_paraguay.wizard.libro_iva'].browse(id)
        move_actual = None
        i = 2
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        # if record.account_ids:
        #     lineas_asiento = request.env['account.move.line'].search(
        #         [('move_id.date', '>=', record.desde), ('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted'),('account_id','in',record.account_ids.mapped('id'))])
        # else:
        #     lineas_asiento = request.env['account.move.line'].search(
        #         [('move_id.date', '>=', record.desde), ('move_id.date', '<=', record.hasta),
        #          ('move_id.state', '=', 'posted')])
        # lineas_asiento = lineas_asiento.sorted(key=lambda p: (p.account_id.code, p.move_id.date))
        # request.model = request.env.context.get('active_model')
        # docs = request.env[request.model].browse(request.env.context.get('active_id'))
        docs = record
        list_get_libro_iva = docs.get_datos_libro_iva(docs.fecha_inicio, docs.fecha_fin, docs.tipo, docs.borrador,
                                                      docs.usuario_id, docs.company_id, docs.cancelado)
        fac = list_get_libro_iva[0]
        lista_totales = list_get_libro_iva[1]
        nc_totales = list_get_libro_iva[2]
        nota_credito = list_get_libro_iva[3]

        tipo_libro_iva = ''
        if docs.tipo == 'venta':
            tipo_libro_iva = 'Venta'
        else:
            tipo_libro_iva = 'Compra'
        sheet = workbook.add_worksheet('Libro IVA')
        bold = workbook.add_format({'bold': True, 'fg_color': 'gray', 'align': 'center'})
        bold_number = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#.##0'})
        border = workbook.add_format({'border': 1})
        # Create a format to use in the merged range.
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#F15F40',
            'font_color': 'white'})

        number_format = workbook.add_format({'align': 'right', 'num_format': '#.##0'})
        # sheet.merge_range('A1:G1', 'LIBRO IVA', merge_format)
        if docs.company_id:
            compania = docs.company_id.name + ' '
        else:
            compania = ''
        sheet.merge_range('A1:O1', compania + 'LIBRO IVA ' + tipo_libro_iva + ' LEY 125/91 DEL ' + str(
            docs.fecha_inicio) + ' AL ' + str(docs.fecha_fin), merge_format)
        sheet.set_column('A:M', 25)
        sheet.write(1, 0, 'Fecha.', bold)
        sheet.write(1, 1, 'Tipo Factura', bold)
        sheet.write(1, 2, 'Timbrado', bold)
        sheet.write(1, 3, 'Nro Factura', bold)
        sheet.write(1, 4, 'Razon Social', bold)
        sheet.write(1, 5, 'Ruc', bold)
        sheet.write(1, 6, 'Gravada 10%', bold)
        sheet.write(1, 7, 'IVA 10%', bold)
        sheet.write(1, 8, 'Gravada 5%', bold)
        sheet.write(1, 9, 'IVA 5%', bold)
        sheet.write(1, 10, 'Exentas', bold)
        sheet.write(1, 11, 'Total', bold)
        sheet.write(1, 12, 'Cuentas', bold)
        if docs.tipo == 'compra':
            sheet.write(1, 13, 'Tipo IVA', bold)
            sheet.write(1, 14, 'Virtual/Elec.', bold)
        acumulador = 0
        cuenta_actual = None
        debito_total = 0
        credito_total = 0
        saldo_total = 0
        saldo_cuenta = 0

        for l in fac:
            if l[0].id == 7727:
                print('HOLA')
            # if l.account_id != cuenta_actual:
            # acumulador = 0
            # cuenta_actual = l.account_id
            # debito_total = 0
            # credito_total = 0
            # saldo_cuenta = 0
            # sheet.write(i,2,l.account_id.code + ' , ' + l.account_id.name)
            i = i + 1
            if l[0].move_type in ('out_refund', 'in_refund'):
                tipo = 'NCR'
            elif l[0].codigo_hechauka == 2:
                tipo = 'NDEB'
            elif l[0].tipo_factura == '1':
                tipo = 'CONT'

            else:
                tipo = 'CRE'
            rucd = ''
            if l[0].partner_no_despachante:
                if l[0].partner_no_despachante.parent_id:
                    partner = l[0].partner_no_despachante.parent_id.name
                    rucd = l[0].partner_no_despachante.parent_id.vat or l[
                        0].partner_no_despachante.parent_id.rucdv or ''
                else:
                    partner = l[0].partner_no_despachante.name
                    rucd = l[0].partner_no_despachante.vat or l[0].partner_no_despachante.rucdv or ''
            elif l[0].partner_id.parent_id.name:
                partner = l[0].partner_id.parent_id.name
                rucd = l[0].partner_id.parent_id.vat or l[0].partner_id.parent_id.rucdv or ''
            else:
                partner = l[0].partner_id.name
                rucd = l[0].partner_id.vat or l[0].partner_id.rucdv or ''

            if l[0].state == 'cancel':
                total = 0
            else:
                if l[0].currency_id != l[0].company_id.currency_id:
                    total = docs.convertir_guaranies(l[0])
                else:
                    total = docs.agregar_punto_de_miles(l[0].amount_total, 1)

            cuentas = l[0].invoice_line_ids.mapped('account_id')
            nom_cuentas = ''
            for cue in cuentas:
                nom_cuentas += '' + cue.name + '/'

            sheet.write(i, 0, str(l[0].invoice_date))
            sheet.write(i, 1, tipo)
            sheet.write(i, 2, l[0].timbrado)
            sheet.write(i, 3, l[0].nro_factura)
            sheet.write(i, 4, partner)
            sheet.write(i, 5, rucd)
            sheet.write(i, 6, docs.agregar_punto_de_miles(abs(l[1][0]), l[0].currency_id.id), number_format)
            sheet.write(i, 7, docs.agregar_punto_de_miles(abs(l[1][1]), l[0].currency_id.id), number_format)
            sheet.write(i, 8, docs.agregar_punto_de_miles(abs(l[1][2]), l[0].currency_id.id), number_format)
            sheet.write(i, 9, docs.agregar_punto_de_miles(abs(l[1][3]), l[0].currency_id.id), number_format)
            sheet.write(i, 10, docs.agregar_punto_de_miles(abs(l[1][4]), l[0].currency_id.id), number_format)
            total = 0
            total = abs(l[1][0]) + abs(l[1][1]) + abs(l[1][2]) + abs(l[1][3]) + abs(l[1][4])
            sheet.write(i, 11, total, number_format)
            sheet.write(i, 12, nom_cuentas)
            if docs.tipo == 'compra':
                tipo_iva = ' '
                if l[0].tipo_iva_id:
                    tipo_iva = l[0].tipo_iva_id.name
                sheet.write(i, 13, tipo_iva)
                if l[0].virtual:
                    sheet.write(i, 14, 1)
                else:
                    sheet.write(i, 14, 0)

            # sheet.write(i, 1, l.move_id.num_asiento)
            # sheet.write(i, 2, l.name)
            # sheet.write(i,3,l.debit)
            # sheet.write(i,4,l.credit)
            # saldo_cuenta = saldo_cuenta + l.balance
            # sheet.write(i,5,saldo_cuenta)
            # debito_total = l.debit + debito_total
            # credito_total = l.credit + credito_total
            # acumulador = acumulador + 1
        # else:
        #     sheet.write(i, 0, l.move_id.date)
        #     sheet.write(i, 1, l.move_id.num_asiento)
        #     sheet.write(i, 2, l.name)
        #     sheet.write(i, 3, l.debit)
        #     sheet.write(i, 4, l.credit)
        #     saldo_cuenta = saldo_cuenta + l.balance
        #     sheet.write(i, 5, saldo_cuenta)
        #     debito_total = l.debit + debito_total
        #     credito_total = l.credit + credito_total
        #     acumulador = acumulador + 1
        #     i = i + 1
        if len(lista_totales) > 4:
            i += 1
            sheet.write(i, 2, 'Total de Facturas:', bold)
            sheet.write(i, 6, docs.agregar_punto_de_miles(abs(lista_totales[0]), 1), bold_number)
            sheet.write(i, 7, docs.agregar_punto_de_miles(abs(lista_totales[1]), 1), bold_number)
            sheet.write(i, 8, docs.agregar_punto_de_miles(abs(lista_totales[2]), 1), bold_number)
            sheet.write(i, 9, docs.agregar_punto_de_miles(abs(lista_totales[3]), 1), bold_number)
            sheet.write(i, 10, docs.agregar_punto_de_miles(abs(lista_totales[4]), 1), bold_number)
            list_tot = 0
            list_tot = abs(lista_totales[0]) + abs(lista_totales[1]) + abs(lista_totales[2]) + abs(
                lista_totales[3]) + abs(lista_totales[4])

            # sheet.write(i, 11, docs.agregar_punto_de_miles(abs(sum(lista_totales)), 1), bold_number)
            sheet.write(i, 11, docs.agregar_punto_de_miles(abs(list_tot), 1), bold_number)
        i += 4
        sheet.write(i, 2, 'NOTAS DE CREDITOS', bold)
        i += 1
        sheet.write(i, 0, 'Fecha.', bold)
        sheet.write(i, 1, 'Tipo Factura', bold)
        sheet.write(i, 2, 'Timbrado', bold)
        sheet.write(i, 3, 'Nro Factura', bold)
        sheet.write(i, 4, 'Razon Social', bold)
        sheet.write(i, 5, 'Ruc', bold)
        sheet.write(i, 6, 'Gravada 10%', bold)
        sheet.write(i, 7, 'IVA 10%', bold)
        sheet.write(i, 8, 'Gravada 5%', bold)
        sheet.write(i, 9, 'IVA 5%', bold)
        sheet.write(i, 10, 'Exentas', bold)
        sheet.write(i, 11, 'Total', bold)
        sheet.write(i, 12, 'Cuentas', bold)
        if docs.tipo == 'compra':
            sheet.write(1, 12, 'Tipo IVA', bold)
            sheet.write(1, 13, 'Cuentas', bold)

        for l in nota_credito:
            # if l.account_id != cuenta_actual:
            # acumulador = 0
            # cuenta_actual = l.account_id
            # debito_total = 0
            # credito_total = 0
            # saldo_cuenta = 0
            # sheet.write(i,2,l.account_id.code + ' , ' + l.account_id.name)
            i = i + 1
            if l[0].move_type in ('out_refund', 'in_refund'):
                tipo = 'NCR'
            elif l[0].codigo_hechauka == 2:
                tipo = 'NDEB'
            elif l[0].tipo_factura == '1':
                tipo = 'CONT'
            else:
                tipo = 'CRE'
            rucd = None
            if l[0].partner_no_despachante:
                if l[0].partner_no_despachante.parent_id:
                    partner = l[0].partner_no_despachante.parent_id.name
                    rucd = l[0].partner_no_despachante.parent_id.rucdv or l[
                        0].partner_no_despachante.parent_id.vat or ''
                else:
                    partner = l[0].partner_no_despachante.name
                    rucd = l[0].partner_no_despachante.rucdv or l[0].partner_no_despachante.vat or ''
            elif l[0].partner_id.parent_id.name:
                partner = l[0].partner_id.parent_id.name
                rucd = l[0].partner_id.parent_id.rucdv or l[0].partner_id.parent_id.vat or ''
            else:
                partner = l[0].partner_id.name
                rucd = l[0].partner_id.rucdv or l[0].partner_id.vat or ''

            if l[0].state == 'cancel':
                total = 0
            else:
                if l[0].currency_id != l[0].company_id.currency_id:
                    total = docs.convertir_guaranies(l[0])
                else:
                    total = docs.agregar_punto_de_miles(l[0].amount_total, 1)

            cuentas = l[0].invoice_line_ids.mapped('account_id')
            nom_cuentas = ''
            for cue in cuentas:
                nom_cuentas += '' + cue.name + '/'

            sheet.write(i, 0, str(l[0].invoice_date))
            sheet.write(i, 1, tipo)
            sheet.write(i, 2, l[0].timbrado)
            sheet.write(i, 3, l[0].nro_factura)
            sheet.write(i, 4, partner)
            sheet.write(i, 5, rucd)
            sheet.write(i, 6, docs.agregar_punto_de_miles(abs(l[1][0]), l[0].currency_id.id), number_format)
            sheet.write(i, 7, docs.agregar_punto_de_miles(abs(l[1][1]), l[0].currency_id.id), number_format)
            sheet.write(i, 8, docs.agregar_punto_de_miles(abs(l[1][2]), l[0].currency_id.id), number_format)
            sheet.write(i, 9, docs.agregar_punto_de_miles(abs(l[1][3]), l[0].currency_id.id), number_format)
            sheet.write(i, 10, docs.agregar_punto_de_miles(abs(l[1][4]), l[0].currency_id.id), number_format)
            total = 0
            total = abs(l[1][0]) + abs(l[1][1]) + abs(l[1][2]) + abs(l[1][3]) + abs(l[1][4])
            sheet.write(i, 11, abs(total))
            sheet.write(i, 12, nom_cuentas)
            if docs.tipo == 'compra':
                tipo_iva = ' '
                if l[0].tipo_iva_id:
                    tipo_iva = l[0].tipo_iva_id.name
                sheet.write(i, 12, tipo_iva)
                sheet.write(i, 13, nom_cuentas)

        if len(nc_totales) > 4:
            i += 1
            sheet.write(i, 2, 'Total de Notas de Credito:', bold)
            sheet.write(i, 6, docs.agregar_punto_de_miles(abs(nc_totales[0]), 1), bold_number)
            sheet.write(i, 7, docs.agregar_punto_de_miles(abs(nc_totales[1]), 1), bold_number)
            sheet.write(i, 8, docs.agregar_punto_de_miles(abs(nc_totales[2]), 1), bold_number)
            sheet.write(i, 9, docs.agregar_punto_de_miles(abs(nc_totales[3]), 1), bold_number)
            sheet.write(i, 10, docs.agregar_punto_de_miles(abs(nc_totales[4]), 1), bold_number)
            total_nc = abs(nc_totales[0]) + abs(nc_totales[1]) + abs(nc_totales[2]) + abs(nc_totales[3]) + abs(
                nc_totales[4])
            sheet.write(i, 11, docs.agregar_punto_de_miles(abs(total_nc), 1), bold_number)

        workbook.close()
        fp.seek(0)
        return request.make_response(fp.read(),
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition('libro_iva.xlsx'))])
