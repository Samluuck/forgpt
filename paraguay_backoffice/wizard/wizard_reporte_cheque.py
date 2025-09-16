# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class WizardReportCheques(models.TransientModel):
    _name = "paraguay_backoffice.wizard.cheques"

    tipo = fields.Selection([('propio','Propios'),('terceros','Terceros')],default='propio')
    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta")
    chequera = fields.Many2one('account.checkbook')
    banco=fields.Many2one('res.bank')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self._get_default_company())


    @api.model
    def _get_default_company(self):
        return self.env.company.id

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin', 'chequera'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin', 'chequera'])[0])
        return self.env.ref('paraguay_backoffice.report_cheque').report_action(self, data)

    def agregar_punto_de_miles(self, numero):
        numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    def convertir_guaranies(self, factura):
        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.date_invoice))])
        monto = factura.amount_total * (1 / rate.rate)
        monto = self.agregar_punto_de_miles(monto, 1)
        return monto


class ReporteCheques(models.AbstractModel):
    _name = 'report.paraguay_backoffice.cheques_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        if docs.tipo == 'propio':
            domain=[('company_id','=',docs.company_id.id),('checkbook_id','=',docs.chequera.id)]
            if docs.fecha_inicio and docs.fecha_fin:
                domain+=[('issue_date','>=',docs.fecha_inicio),('issue_date','<=',docs.fecha_fin)]
            if docs.fecha_inicio and not docs.fecha_fin:
                raise ValidationError('Falta fecha final')
            if  not docs.fecha_inicio and docs.fecha_fin:
                raise ValidationError('Falta fecha inicial')
            cheques=self.env['account.check'].search(domain,order='name')
            cheques_terceros=None
        else:
            domain = [('company_id','=',docs.company_id.id),('issue_date', '>=', docs.fecha_inicio), ('issue_date', '<=', docs.fecha_fin)]
            if docs.banco:
                domain+=[('bank_id','=',docs.banco.id)]
            cheques_terceros = self.env['account.check.third'].search(domain, order='issue_date')
            cheques=None


        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'cheques':cheques,
            'cheques_terceros':cheques_terceros
        }
        return docargs












