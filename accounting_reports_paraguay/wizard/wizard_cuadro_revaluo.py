# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
_logger = logging.getLogger(__name__)

class WizardRevaluo(models.TransientModel):
    _name = "cuadro.revaluo.wizard"

    periodo = fields.Many2one('account.fiscal.year',string='Periodo fiscal',required=True)
    fecha_inicio = fields.Date(related='periodo.date_from', string="Fecha desde")
    fecha_fin = fields.Date(related='periodo.date_to', string="Fecha hasta")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())


    @api.model
    def _get_default_company(self):
        return self.env.company.id

    # @api.multi
    def check_report(self):
        _logger.info('SELFFFFFFF %s', self)
        data = {}
        data['form'] = isinstance(self.read(['fecha_inicio', 'fecha_fin']), list) and \
                       self.read(['fecha_inicio', 'fecha_fin'])[0] or self.read(['fecha_inicio', 'fecha_fin'])
        _logger.warning('DATA %s', data)
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.cuadro_revaluo_id').report_action(self, data)

    def agregar_punto_de_miles(self, numero):
        if numero >= 0:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        else:
            numero*=-1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            numero_con_punto='-'+numero_con_punto
        num_return = numero_con_punto
        return num_return


    def formatear_fecha(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fd = datetime.strftime(fi, '%d/%m/%Y')

        return fd

    def get_vida_util(self,periodo,bien):
        years = abs(relativedelta(bien.acquisition_date,
                                  periodo.date_to).years)  # anhos entre fecha de compra y fecha actual
        valor = bien.method_number - years
        if valor > 0:
            return valor
        else:
           return 0

    def ultima_depreciacion(self,bien):
        if bien.ultima_depreciacion:
            if bien.ultima_depreciacion.date >= self.fecha_inicio and bien.ultima_depreciacion.date <= self.fecha_fin:
                return True
            else:
                return False
        else:
           return False

    def get_coeficiente(self,periodo):
        # coeficiente = self.env['account.revaluo'].search([('periodo','=',periodo.id),('tipo','=','amortizacion')])
        # if len(coeficiente) > 0:
        #     return coeficiente.coeficiente
        return 0

    def get_bienes_categoria(self, fecha_inicio, fecha_fin,categoria):
        """
        La idea es un dicionario que tenga la cuenta y el total sumado
        :param fecha_inicio:
        :param fecha_fin:
        :param company_id:
        :return:

        """
        bienes = self.env['account.asset'].search([('model_id','=',categoria.id),('state','!=','close'),('acquisition_date','<',fecha_fin),('disposal_date', '=', False)]).sorted(key=lambda x: x.acquisition_date)
        _logger.warning('BIENES %s', bienes)
        bienes_vendidos = self.env['account.asset'].search([('disposal_date','>=',fecha_fin)]).sorted(key=lambda x: x.disposal_date)
        _logger.warning('BIENES VENDIDOS %s', bienes_vendidos)
        if len(bienes_vendidos) > 0 :
            bienes = bienes + bienes_vendidos
        _logger.warning('AMBOS %s', bienes)
        return bienes

class ReporteLibroCompras(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.cuadro_revaluo_report'





    # @api.multi
    def _get_report_values(self, docids, data=None):
        # _logger.info('SELF %s', self)
        # _logger.info('SELF CONTEXT %s', self.env.context)
        # _logger.info('SELF active %s', self.env.context.get('active_model'))

        model = self.env.context.get('active_model')
        _logger.info('MODELLL %S', model)
        docs = self.env[model].browse(self.env.context.get('active_id'))
        _logger.info('DOCS %s', docs)

        categorias = self.env['account.asset'].search([('asset_type', '=', 'purchase'), ('state', '=', 'model')])
        _logger.info('CATEGORIAS %s', categorias)


        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'categorias': categorias,


        }
        _logger.info('docargsss %s', docargs)
        return docargs
