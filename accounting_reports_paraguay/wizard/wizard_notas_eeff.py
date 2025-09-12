# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
_logger = logging.getLogger(__name__)

class WizardNotasEEFF(models.TransientModel):
    _name = "notas.wizard.notas.eeff"


    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())


    @api.model
    def _get_default_company(self):
        return self.env.company.id

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.notas_eeff_id').report_action(self, data)

    def agregar_punto_de_miles(self, numero):
        if numero < 0:
            numero*=-1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            num_return='-'+numero_con_punto
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            num_return = numero_con_punto
        return num_return

    def convertir_guaranies(self, factura):
        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.date_invoice))])
        monto = factura.amount_total * (1 / rate.rate)
        monto = self.agregar_punto_de_miles(monto, 1)
        return monto

    def obtener_anio_actual(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        anio = fi.year
        return anio
    def obtener_anio_anterior(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year
        return anio

    def formatear_fecha(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fd = datetime.strftime(fi, '%d/%m/%Y')
        return fd

    def montos_por_empresa(self,cuentas,fecha_inicio,fecha_fin):
        datos=collections.OrderedDict()

        f1 = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        f2 = datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant = f1 - relativedelta(years=1)
        fecha_fin_ant = f2 - relativedelta(years=1)

        movimientos_actuales=self.env['account.move.line'].search([('account_id','in',cuentas.ids),('partner_id','!=', False),('date','>=',fecha_inicio),('date','<=',fecha_fin)],order='partner_id')
        movimientos_anterior=self.env['account.move.line'].search([('account_id','in',cuentas.ids),('partner_id','!=', False),('date','>=',fecha_inicio_ant),('date','<=',fecha_fin_ant),('move_id.cierre','=',False)],order='partner_id')
        empresas=movimientos_actuales.mapped('partner_id')

        for e in empresas:
            valor=sum([i.balance for i in movimientos_actuales.filtered(lambda r:r.partner_id.id==e.id)])
            valor_ant=sum([i.balance for i in movimientos_anterior.filtered(lambda r:r.partner_id.id==e.id)])
            if valor>0:
                datos.setdefault(e,[valor,valor_ant])
        return datos.items()



    def montos_cuentas(self,cuenta,fecha_inicio,fecha_fin):
        query = """SELECT sum(balance) FROM account_move_line aml join account_move am on aml.move_id=am.id WHERE aml.account_id= '%s' AND aml.date >= '%s' AND aml.date<= '%s' AND am.cierre = FALSE """

        f1 = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        f2 = datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant = f1 - relativedelta(years=1)
        fecha_fin_ant = f2 - relativedelta(years=1)

        self.env.cr.execute(query % (str(cuenta.id),str(fecha_inicio),str(fecha_fin)))
        results = self.env.cr.dictfetchall()

        self.env.cr.execute(query % (str(cuenta.id), str(fecha_inicio_ant), str(fecha_fin_ant)))
        results2 = self.env.cr.dictfetchall()

        valor_actual=self.agregar_punto_de_miles(results[0]['sum'] or 0)
        valor_anterior=self.agregar_punto_de_miles(results2[0]['sum'] or 0)

        return [valor_actual,valor_anterior]


class ReporteLibroCompras(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.notas_eeff_report'

    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        # Obtener las fechas del wizard y convertirlas en años
        fecha_inicio = docs.fecha_inicio.year
        fecha_fin = docs.fecha_fin.year

        # Filtrar los registros de Anexo5 que coincidan con el rango de años
        anexo5_records = self.env['account_reports_paraguay.anexo5'].search([
            ('periodo', '>=', fecha_inicio),
            ('periodo', '<=', fecha_fin)
        ], limit=1)

        # Agregar los registros de Anexo5 a docargs
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'anexo5': anexo5_records,  # Incluyendo los registros de Anexo5
        }
        return docargs




