import logging
import calendar
from odoo import api, fields, models, tools, _
from datetime import date, timedelta, datetime

_logger = logging.getLogger(__name__)


class HrPayRollWizard(models.TransientModel):
    _name = "hr_set_wizard_view"
    start_date = fields.Date(string="Fecha Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    type_reports = fields.Selection([('6', 'Registros de Sueldos y Jornales')], string="Reporte de:", default='6')

    def check_report_syj(self):
        data = {}
        data['form'] = self.read(['type_reports'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(
            self.read(['start_date', 'end_date', 'type_reports'])[0]
        )
        return self.env.ref(
            'hr_set.hr_set_report_action'
        ).report_action(self, data)


class ReportPayRollXLSXWizard(models.AbstractModel):
    _name = 'report.hr_set.payroll_report_xlsx'
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
        column_names = [
            cursor.description[cur][0]
            for cur in range(len(cursor.description))
        ]
        return column_names

    def generate_xlsx_report(self, workbook, data, wizard):
        _logger.debug('Generando reporte en generate_xlsx_report')
        date_start = wizard.start_date
        date_end = wizard.end_date
        year_period = date_start.year if date_start else date.today().year

        company_name = self.env.user.company_id.name
        telefono_empresa = self.env.user.company_id.phone
        web = self.env.user.company_id.website
        sheet = workbook.add_worksheet()

        canecera_principal = workbook.add_format({
            'align': 'center',
            'font_size': 13,
            'bold': True,
        })
        body_format = workbook.add_format({
            'align': 'center',
            'font_size': 10,
            'bold': True,
        })

        sheet.write(1, 0, 1, canecera_principal)
        sheet.write(4, 0, 'DETALLE', canecera_principal)
        sheet.write(0, 1, 'RUC DECLARANTE', canecera_principal)
        sheet.write(1, 1, self.env.user.company_id.ruc or ';', canecera_principal)
        sheet.write(0, 2, "PERIODO", canecera_principal)
        sheet.write(1, 2, year_period, canecera_principal)
        sheet.write(0, 3, "CANTIDAD DE EMPLEADOS", canecera_principal)
        sheet.write(0, 4, "SUMA MONTO TOTAL", canecera_principal)


        headers = [
            "DETALLE", "RUC/N° DE DOCUMENTO", "DV", "PRIMER APELLIDO", "SEGUNDO APELLIDO",
            "PRIMER NOMBRE", "SEGUNDO NOMBRE", "TIPO DE PAGO", "MONTO BRUTO (SIN DESCUENTO)",
            "DESCUENTO POR JUBILACION", "DESCUENTO POR SEGURO SOCIAL", "OTROS DESCUENTOS",
            "MONTO AGUINALDO", "CORREO ELECTRONICO", "DEPARTAMENTO", "DISTRITO",
            "LOCALIDAD/BARRIO", "DIRECCION COMPLETA", "PREFIJO LINEA FIJA", "TELEFONO LINEA FIJA",
            "PREFIJO CELULAR", "TELEFONO CELULAR", "TIPO DE EMPLEADO"
        ]

        for col, header in enumerate(headers):
            sheet.write(4, col, header, canecera_principal)

        payslip_records = self.env['hr.payslip'].search([
            ('date_from', '>=', date_start),
            ('date_to', '<=', date_end),
            ('struct_id.es_liquidacion_despido', '=', False),
            ('struct_id.es_liquidacion_despido_injustificado', '=', False),
            ('struct_id.es_liquidacion_renuncia', '=', False)
        ])

        empleados_data = {}
        for payslip in payslip_records:
            employee = payslip.employee_id

            # Separar el nombre eliminando la coma y el espacio
            name_parts = [part.strip() for part in employee.name.replace(",", "").split()] if employee.name else [';']

            # Determinar nombres y apellidos
            # primer_apellido = name_parts[0] if len(name_parts) > 0 else ';'
            # segundo_apellido = name_parts[1] if len(name_parts) > 2 else ';'
            # primer_nombre = name_parts[-2] if len(name_parts) > 1 else ';'
            # segundo_nombre = name_parts[-1] if len(name_parts) > 1 else ';'

            primer_apellido = employee.primer_apellido if employee.primer_apellido else ';'
            segundo_apellido = employee.segundo_apellido if employee.segundo_apellido else ';'
            primer_nombre = employee.primer_nombre if employee.primer_nombre else ';'
            segundo_nombre = employee.segundo_nombre if employee.segundo_nombre else ';'

            # Extraer el teléfono del empleado
            phone_number = employee.phone or ''

            # Extraer el prefijo celular y el número celular
            prefijo_celular = ''
            telefono_celular = ''

            import re
            match = re.match(r"\+595\s?(\d{3})\s?(\d{6})", phone_number)
            if match:
                prefijo_celular = match.group(1)  # Primer grupo: Prefijo de 3 dígitos
                telefono_celular = match.group(2)  # Segundo grupo: Últimos 6 dígitos

            if employee.id not in empleados_data:
                empleados_data[employee.id] = {
                    'detalle': 2,
                    'documento': employee.identification_id or ';',
                    'dv': ';',
                    'primer_apellido': primer_apellido,
                    'segundo_apellido': segundo_apellido,
                    'primer_nombre': primer_nombre,
                    'segundo_nombre': segundo_nombre,
                    'tipo_pago': dict(employee._fields['tipo_pago_set'].selection).get(employee.tipo_pago_set, ';'),
                    'monto_bruto': 0,
                    'jubilacion': 0,
                    'seguro_social': 0,
                    'otros_descuentos': 0,
                    'aguinaldo': 0,
                    'correo': employee.work_email or ';',
                    'departamento': dict(employee._fields['departamento_set'].selection).get(employee.departamento_set, ';'),
                    'distrito': dict(employee._fields['distrito_set'].selection).get(employee.distrito_set, ';'),
                    'barrio': employee.address_home_id.zip if employee.address_home_id and employee.address_home_id.zip else ';',
                    'direccion': employee.address_home_id.street if employee.address_home_id and employee.address_home_id.street else ';',
                    'prefijo_linea_fija': '',
                    'telefono_fijo': '',
                    'prefijo_celular': prefijo_celular,
                    'telefono_celular': telefono_celular,
                    'tipo_empleado': dict(employee._fields['tipo_empleado_set'].selection).get(employee.tipo_empleado_set, ';')
                }

            for line in payslip.line_ids:
                rule = line.salary_rule_id  # Obtener la regla salarial

                # Si existe una regla con bruto_set marcado, buscamos si hay una línea con código 'BRUTO'
                if rule.bruto_set:
                    bruto_line = next((l for l in payslip.line_ids if l.salary_rule_id.code == 'BRUTO'), None)

                    if bruto_line:
                        _logger.debug(
                            f"Empleado ID {employee.id}: Se encontró línea con código 'BRUTO', asignando {bruto_line.total} a monto_bruto"
                        )
                        empleados_data[employee.id][
                            'monto_bruto'] = bruto_line.total  # Tomamos el valor de la línea BRUTO
                    else:
                        _logger.debug(
                            f"Empleado ID {employee.id}: No se encontró línea con código 'BRUTO', sumando {line.total} a monto_bruto"
                        )
                        empleados_data[employee.id][
                            'monto_bruto'] += line.total  # Sigue sumando como antes si no hay BRUTO

                if rule.desc_jubi:  # Verifica si "Descuento jubilación SET" está marcado
                    _logger.debug(
                        f"Empleado ID {employee.id}: Sumando {line.total} a jubilacion (antes: {empleados_data[employee.id]['jubilacion']})"
                    )
                    empleados_data[employee.id]['jubilacion'] += line.total
                    _logger.debug(
                        f"Empleado ID {employee.id}: Nuevo jubilacion: {empleados_data[employee.id]['jubilacion']}"
                    )

                if rule.segu_social:  # Verifica si "Descuento por seguro social SET" está marcado
                    _logger.debug(
                        f"Empleado ID {employee.id}: Sumando {line.total} a seguro_social (antes: {empleados_data[employee.id]['seguro_social']})"
                    )
                    empleados_data[employee.id]['seguro_social'] += line.total
                    _logger.debug(
                        f"Empleado ID {employee.id}: Nuevo seguro_social: {empleados_data[employee.id]['seguro_social']}"
                    )

                if rule.ot_desc:  # Verifica si "Otros descuentos SET" está marcado
                    _logger.debug(
                        f"Empleado ID {employee.id}: Sumando {line.total} a otros_descuentos (antes: {empleados_data[employee.id]['otros_descuentos']})"
                    )
                    empleados_data[employee.id]['otros_descuentos'] += line.total
                    _logger.debug(
                        f"Empleado ID {employee.id}: Nuevo otros_descuentos: {empleados_data[employee.id]['otros_descuentos']}"
                    )

                if rule.aguinaldo_set:  # Verifica si "Aguinaldo SET" está marcado
                    _logger.debug(
                        f"Empleado ID {employee.id}: Sumando {line.total} a aguinaldo (antes: {empleados_data[employee.id]['aguinaldo']})"
                    )
                    empleados_data[employee.id]['aguinaldo'] += line.total
                    _logger.debug(
                        f"Empleado ID {employee.id}: Nuevo aguinaldo: {empleados_data[employee.id]['aguinaldo']}"
                    )

        sheet.write(1, 3, len(empleados_data), canecera_principal)  # Cantidad de empleados total
        sheet.write(1, 4, sum(data['monto_bruto'] for data in empleados_data.values()), canecera_principal) #Cantidad bruto total

        row = 5
        for data in empleados_data.values():
            sheet.write_row(row, 0, list(data.values()), body_format)
            row += 1

        _logger.debug('Reporte generado exitosamente')


# import logging
# import calendar
# from odoo import api, fields, models, tools, _
# from datetime import date, timedelta , datetime
#
# _logger = logging.getLogger(__name__)
#
#
# class HrPayRollWizard(models.TransientModel):
#
#     _name = "hr_set_wizard_view"
#     start_date = fields.Date(string="Fecha Inicio", required=True)
#     end_date = fields.Date(string="Fecha Final", required=True)
#     type_reports = fields.Selection([('6', 'Registros de Sueldos y Jornales')],string="Reporte de:", default='6')
#
#     def check_report_syj(self):
#         data = {}
#         data['form'] = self.read(['type_reports'])[0]
#         return self._print_report(data)
#     def _print_report(self, data):
#         data['form'].update(
#             self.read(['start_date', 'end_date', 'type_reports'])[0])
#         return self.env.ref(
#             'hr_set.hr_set_report_action'
#         ).report_action(self, data)
#
# class ReportPayRollXLSXWizard(models.AbstractModel):
#     _name = 'report.hr_set.payroll_report_xlsx'
#     _inherit = 'report.report_xlsx.abstract'
#
#     def create_worksheet_file(self, workbook, column_names, list_values):
#         _logger.debug("create_worksheet_file")
#         sheet = workbook.add_worksheet()
#         row = 0
#         for col, names in enumerate(column_names):
#             sheet.write(row, col, names)
#
#         for result in list_values:
#             row += 1
#             for col, value in enumerate(result):
#                 sheet.write(row, col, value)
#     def get_columns_names(self, cursor):
#         _logger.debug("get_columns_names")
#         column_names = list()
#         column_names = [
#             cursor.description[cur][0]
#             for cur in range(len(cursor.description))
#         ]
#         return column_names
#
#     def generate_xlsx_report(self, workbook, data, wizard):
#         _logger.debug('Este es un mensaje de aviso que ha ingresado a generate_xlsx_report')
#         # Obteniendo los datos desde el wizard
#         date_start = wizard.start_date
#         date_end = wizard.end_date
#         company_name = self.env.user.company_id.name #nombre de la compañia
#         telefono_empresa = self.env.user.company_id.phone #tel de la compañia
#         web= self.env.user.company_id.website #sitio de la compañia
#         sheet = workbook.add_worksheet()
#         ################## Definición de formatos #####################3
#         canecera_principal = workbook.add_format({
#             'align': 'center',
#             'font_size': 13,
#             'bold': True,
#
#         })
#         body_format= workbook.add_format({
#             'align': 'center',
#             'font_size': 10,
#             'bold': True,
#         })
#
#         print('***** Este mensaje indica que el repo *****')
#         #### Valor por defecto obligatorio 1  ###
#         sheet.write(1, 0, 1, canecera_principal)
#         ### Colimna de detalles
#         ### El valor por defecto 2 #######
#         sheet.write(4, 0,'DETALLE', canecera_principal)
#         # #### Extraemos el ruc de la compañia ###
#         sheet.write(0, 1, 'RUC DECLARANTE', canecera_principal)
#         sheet.write(1, 1, 123456, canecera_principal)
#         ##### Extraemos la fecha del rengo de fecha que se estira ###
#         sheet.write(0, 2, "PERIODO", canecera_principal)
#         sheet.write(1, 2, 2025, canecera_principal)
#         sheet.write(0, 3, "CANTIDAD DE EMPLEADOS", canecera_principal)
#         sheet.write(1, 3, 25, canecera_principal)
#         sheet.write(0, 4, "SUMA MONTO TOTAL", canecera_principal)
#         sheet.write(1, 4, 1205013215, canecera_principal)
#         sheet.write(4, 1,'RUC/N° DE DOCUMENTO', canecera_principal)
#         sheet.write(4, 2, "DV", canecera_principal)
#         sheet.write(4, 3, "PRIMER APELLIDO", canecera_principal)
#         sheet.write(4, 4, "SEGUNDO APELLIDO", canecera_principal)
#         sheet.write(4, 5, "PRIMER NOMBRE", canecera_principal)
#         sheet.write(4, 6, "SEGUNDO NOMBRE", canecera_principal)
#         sheet.write(4, 7, "TIPO DE PAGO", canecera_principal)
#         sheet.write(4, 8, "MONTO BRUTO (SIN DESCUENTO)", canecera_principal)
#         sheet.write(4, 9, "DESCUENTO POR JUBILACION", canecera_principal)
#         sheet.write(4, 10, "DESCUENTO POR SEGURO SOCIAL", canecera_principal)
#         sheet.write(4, 11, "OTROS DESCUENTOS", canecera_principal)
#         sheet.write(4, 12, "MONTO AGUINALDO", canecera_principal)
#         sheet.write(4, 13, "CORREO ELECTRONICO", canecera_principal)
#         sheet.write(4, 14, "DEPARTAMENTO", canecera_principal)
#         sheet.write(4, 15, "DISTRITO", canecera_principal)
#         sheet.write(4, 16, "LOCALIDAD/BARRIO", canecera_principal)
#         sheet.write(4, 17, "DIRECCION COMPLETA", canecera_principal)
#         sheet.write(4, 18, "PREFIJO LINEA FIJA", canecera_principal)
#         sheet.write(4, 19, "TELEFONO LINEA FIJA", canecera_principal)
#         sheet.write(4, 20, "PREFIJO CELULAR", canecera_principal)
#         sheet.write(4, 21, "TELEFONO CELULAR", canecera_principal)
#         sheet.write(4, 22, "TIPO DE EMPLEADO", canecera_principal)
#
#        # Buscar las nóminas dentro del rango de fechas especificado
#         payslip_records = self.env['hr.payslip'].search([
#             ('date_from', '>=', date_start),
#             ('date_to', '<=', date_end)
#         ])
#         empleados_data = {}
#         for payslip in payslip_records:
#             employee = payslip.employee_id
#             if employee.id not in empleados_data:
#                 empleados_data[employee.id] = {
#                     'detalle': 2,
#                     'documento': employee.identification_id or 'No se encuentra cargado el campo',
#                     'dv': '',  # Aquí podrías calcular el dígito verificador si es necesario
#                     'primer_apellido': employee.primer_apellido or 'NO sse encuentra cargado el campo',
#                     'segundo_apellido': employee.segundo_nombre or 'NO se encuentra cargado el campo',
#                     'primer_nombre':  employee.primer_nombre or 'NO se encuentra cargado el campo',
#                     'segundo_nombre': employee.segundo_nombre or 'NO se encuentra cargado el campo' ,
#                     'tipo_pago': 'Mensualero' ,
#                     'monto_bruto': 0,
#                     'jubilacion': 0,
#                     'seguro_social': 0,
#                     'otros_descuentos': 0,
#                     'aguinaldo': 0,
#                     'correo':  employee.work_email or 'NO se encuentra cargado el campo',
#                     'departamento': '',
#                     'distrito':  '',
#                     'barrio':  '',
#                     'direccion': employee.work_email or ' encuentra cargado el campo',
#                     'prefijo_linea_fija': '',  # Agregar lógica si aplica
#                     'telefono_fijo':'',
#                     'prefijo_celular': '',  # Agregar lógica si aplica
#                     'telefono_celular': '',
#                     'tipo_empleado': ''
#                 }
#             # Calcular totales de nómina para el empleado
#             for line in payslip.line_ids:
#                 if line.salary_rule_id.code == 'BRUTO':
#                     empleados_data[employee.id]['monto_bruto'] += line.total
#                 elif line.salary_rule_id.code == 'JUBILACION':
#                     empleados_data[employee.id]['jubilacion'] += line.total
#                 elif line.salary_rule_id.code == 'SEGURO_SOCIAL':
#                     empleados_data[employee.id]['seguro_social'] += line.total
#                 elif line.salary_rule_id.code == 'OTROS_DESCUENTOS':
#                     empleados_data[employee.id]['otros_descuentos'] += line.total
#                 elif line.salary_rule_id.code == 'AGUINALDO':
#                     empleados_data[employee.id]['aguinaldo'] += line.total
#         # Imprimir datos para depuración
#         print(f"Datos procesados para el reporte: {empleados_data}")
#         # Escribir datos en el Excel
#         row = 5
#         for employee_id, data in empleados_data.items():
#             sheet.write(row, 0, data['detalle'], body_format)
#             sheet.write(row, 1, data['documento'], body_format)
#             sheet.write(row, 2, data['dv'], body_format)
#             sheet.write(row, 3, data['primer_apellido'], body_format)
#             sheet.write(row, 4, data['segundo_apellido'], body_format)
#             sheet.write(row, 5, data['primer_nombre'], body_format)
#             sheet.write(row, 6, data['segundo_nombre'], body_format)
#             sheet.write(row, 7, data['tipo_pago'], body_format)
#             sheet.write(row, 8, data['monto_bruto'], body_format)
#             sheet.write(row, 9, data['jubilacion'], body_format)
#             sheet.write(row, 10, data['seguro_social'], body_format)
#             sheet.write(row, 11, data['otros_descuentos'], body_format)
#             sheet.write(row, 12, data['aguinaldo'], body_format)
#             sheet.write(row, 13, data['correo'], body_format)
#             sheet.write(row, 14, data['departamento'], body_format)
#             sheet.write(row, 15, data['distrito'], body_format)
#             sheet.write(row, 16, data['barrio'], body_format)
#             sheet.write(row, 17, data['direccion'], body_format)
#             sheet.write(row, 18, data['prefijo_linea_fija'], body_format)
#             sheet.write(row, 19, data['telefono_fijo'], body_format)
#             sheet.write(row, 20, data['prefijo_celular'], body_format)
#             sheet.write(row, 21, data['telefono_celular'], body_format)
#             sheet.write(row, 22, data['tipo_empleado'], body_format)
#             row += 1
#         print('Reporte generado exitosamente')
