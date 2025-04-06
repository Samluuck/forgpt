
import sys
import logging
import babel
import copy
from datetime import datetime
from time import strptime, strftime, mktime
from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class HrPayRollWizard(models.TransientModel):

    _name = "hr_registro_vacaciones_wizard_view"
    start_date = fields.Date(string="Fecha Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    type_reports = fields.Selection([('5', 'Registros de Vacaciones Anuales')],string="Reporte de:", default='5')

    def check_report(self):
        data = {}
        data['form'] = self.read(['type_reports'])[0]
        return self._print_report(data)
    def _print_report(self, data):
        data['form'].update(
            self.read(['start_date', 'end_date', 'type_reports'])[0])
        return self.env.ref(
            'hr_registro_vacaciones.hr_registro_vacaciones_report_action'
        ).report_action(self, data)

class ReportPayRollXLSXWizard(models.AbstractModel):
    _name = 'report.hr_registro_vacaciones.payroll_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def create_worksheet_file(self, workbook, column_names, list_values):
        _logger.debug("create_worksheet_file")
        sheet = workbook.add_worksheet()
        row = 0
        for col, names in enumerate(column_names):
            sheet.write(row, col, names)

        for result in list_values:
            row += 1
            for col, value in enumerate(result):
                sheet.write(row, col, value)
    def get_columns_names(self, cursor):
        _logger.debug("get_columns_names")
        column_names = list()
        column_names = [
            cursor.description[cur][0]
            for cur in range(len(cursor.description))
        ]

        return column_names
    def get_list_vacaciones(self, start_date, end_date):
        print("-------------------------ENTRA EN get_list_vacaciones----------------------------------")
        holyday_obj = self.env['hr.leave']

        holidays_taken = holyday_obj.search([
            ('request_date_to', '<=', end_date),
            ('request_date_from', '>=', start_date),
            ('holiday_status_id.es_vacacion', '=', True),
            ('state', 'in', ['validate'])
        ])
        return holidays_taken
    def generate_xlsx_report(self, workbook, data, wizard):
        _logger.debug("generate_xlsx_report")
        list_values = list()
        query = ""
        if wizard.type_reports in ("5"):
            df_start_date = fields.Date.from_string(wizard.start_date)
            locale = self.env.context.get('lang') or 'es_ES'
            ttyme = datetime.fromtimestamp(
                mktime(strptime(str(wizard.start_date), "%Y-%m-%d")))
            txt_month = tools.ustr(
                babel.dates.format_date(
                    date=ttyme, format='MMMM', locale=locale))
            if wizard.type_reports == "5":
                list_vacaciones = self.get_list_vacaciones(wizard.start_date, wizard.end_date)
            centrado = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'fg_color': 'c3c3c3',
            })
            centrado_celdas = workbook.add_format({
                'align': 'center',
            })

            sheet = workbook.add_worksheet()

        ####################################################### REPORTE CON FORMATOD DE IMPRESION ############################################################
            if wizard.type_reports == "5":
                nro_actual = 1
                fila_nro = 4
                sheet.merge_range('A3:I3', 'DURACIÓN DE VACACIONES', centrado)
                sheet.write(3, 0, "No.", centrado)
                sheet.merge_range('B4:C4', 'NOMBRE Y APELLIDO', centrado)
                sheet.write(3, 3, "FECHA DE INGRESO", centrado)
                sheet.write(3, 4, "DÍAS", centrado)
                sheet.write(3, 5, "DESDE", centrado)
                sheet.write(3, 6, "HASTA", centrado)
                sheet.write(3, 7, "REMUNERACIÓN", centrado)
                sheet.write(3, 8, "OBSERVACIONES", centrado)
                empleados_vacaciones = list_vacaciones.mapped('employee_id')

                for emple in empleados_vacaciones.sorted(key=lambda r: r.name):



                    contrato_emple = emple.contract_ids.filtered(lambda r: r.state not in ('draft', 'cancel'))
                    salario_por_dia = 0
                    if contrato_emple:
                        salario_contrato = contrato_emple[0].wage
                        salario_por_dia = salario_contrato / 30
                        if len(contrato_emple) > 1:
                            cont_abier = contrato_emple.filtered(lambda r: r.state == 'open')
                            fecha_inicio = cont_abier.date_start if cont_abier else contrato_emple[0].date_start
                        else:
                            fecha_inicio = contrato_emple[0].date_start
                    else:
                        contract_obj = self.env['hr.contract'].search(
                            [('employee_id', '=', emple.id), ('active', '=', False)])
                        fecha_inicio = contract_obj[0].date_start if contract_obj else 'VERIFICAR CONTRATO'

                    vacaciones = list_vacaciones.filtered(lambda r: r.employee_id == emple)



                    dias = 0
                    desde = None
                    hasta = None
                    observaciones = ''
                    monto_vacacion = 0
                    for tod_vac in vacaciones.sorted(key=lambda r: r.request_date_from):
                        dias += tod_vac.number_of_days_display
                        if not desde or tod_vac.request_date_from < desde:
                            desde = tod_vac.request_date_from
                        if not hasta or tod_vac.request_date_to > hasta:
                            hasta = tod_vac.request_date_to
                        if tod_vac.name:
                            observaciones = str(tod_vac.name)
                        # se valida tambien los recibos en el rango de fecha de la ausencia
                        recibo = self.env['hr.payslip'].search([
                            ('employee_id', '=', emple.id),
                            ('date_from', '<=', desde),
                            ('date_to', '>=', hasta)
                        ])
                        for rec in recibo:
                            for line in rec.line_ids:
                                if line.category_id.id == 2:# id del concepto vacacion
                                    monto_vacacion = line.amount
                                #print(line.category_id,line.category_id.name)


                    sheet.write(fila_nro, 0, nro_actual, centrado_celdas)
                    sheet.merge_range(fila_nro, 1, fila_nro, 2, emple.name, centrado_celdas)
                    sheet.write(fila_nro, 3, str(fecha_inicio), centrado_celdas)
                    sheet.write(fila_nro, 4, str(int(dias)), centrado_celdas)
                    if desde:
                        nuevo_formato_desde = desde.strftime('%d-%m-%Y')
                        sheet.write(fila_nro, 5, nuevo_formato_desde, centrado_celdas)
                    if hasta:
                        nuevo_formato_hasta = hasta.strftime('%d-%m-%Y')
                        sheet.write(fila_nro, 6, nuevo_formato_hasta, centrado_celdas)
                    if monto_vacacion == 0:
                        sheet.write(fila_nro, 7, round(salario_por_dia * dias), centrado_celdas)
                    else:
                        sheet.write(fila_nro, 7, round(monto_vacacion), centrado_celdas)
                    sheet.write(fila_nro, 8, observaciones.title(), centrado_celdas)
                    fila_nro += 1
                    nro_actual += 1

