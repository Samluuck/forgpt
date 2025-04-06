import logging
import calendar
from odoo import api, fields, models, tools, _
from datetime import date, timedelta, datetime

_logger = logging.getLogger(__name__)


class HrPayRollWizard(models.TransientModel):
    _name = "hr_resumen_general_wizard_view"
    start_date = fields.Date(string="Fecha Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    type_reports = fields.Selection([('7', 'Resume General de Personas')], string="Reporte de:", default='7')

    def check_report_syj(self):
        data = {}
        data['form'] = self.read(['type_reports'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(
            self.read(['start_date', 'end_date', 'type_reports'])[0])
        return self.env.ref(
            'hr_resumen_general.hr_resumen_general_report_action'
        ).report_action(self, data)


class ReportPayRollXLSXWizard(models.AbstractModel):
    _name = 'report.hr_resumen_general.payroll_report_xlsx'
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
        _logger.debug('Este es un mensaje de aviso que ha ingresado a generate_xlsx_report')
        # Obteniendo los datos desde el wizard
        date_start = wizard.start_date
        date_end = wizard.end_date
        sheet = workbook.add_worksheet()

        ################## Definición de formatos #####################3
        merge_format_head = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#B5B2B2',  # Esto pondrá un fondo amarillo

        })
        formato_contenido = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',

        })
        _logger.debug('Este es un mensaje de aviso que el usuario elige imprimir el reporte en formato de importacion')
        sheet.write(0, 0, "Nropatronal", merge_format_head)
        sheet.write(0, 1, "año", merge_format_head)
        sheet.write(0, 2, "supjefesvarones", merge_format_head)
        sheet.write(0, 3, "supjefesmujeres", merge_format_head)
        sheet.write(0, 4, "empleadosvarones", merge_format_head)
        sheet.write(0, 5, "empleadosmujeres", merge_format_head)
        sheet.write(0, 6, "obrerosvarones", merge_format_head)
        sheet.write(0, 7, "obrerosmujeres", merge_format_head)
        sheet.write(0, 8, "menoresvarones", merge_format_head)
        sheet.write(0, 9, "menoresmujeres", merge_format_head)
        sheet.write(0, 10, "orden", merge_format_head)

        payslip_records = self.env['hr.payslip'].search(
            [('date_from', '>=', wizard.start_date), ('date_to', '<=', wizard.end_date)])
        # Inicializa el conjunto de IDs de supervisores ya contados
        supervisores_contados = set()
        supervisores_contados_mujeres = set()
        empleados_supervisores_nuevos = set()
        empleados_supervisores_nuevos_mujeres = set()
        empleados_supervisores_despedidos_hombres = set()
        empleados_supervisores_despedidos_mujeres = set()
        empleados_hombres = set()
        empleados_mujeres = set()
        empleados_hombres_nuevos = set()
        empleados_mujeres_nuevos = set()
        empleados_hombres_despedidos_hombres = set()
        empleados_despedidos_mujeress = set()
        empleados_jornaleros = set()
        empleados_mujeres_jornaleros = set()
        empleados_jornaleros_nuevos = set()
        empleados_mujeres_jornaleros_nuevos = set()
        empleados_jornaleros_despedidos_hombres = set()
        empleados_jornaleros_despedidos_mujeres = set()
        empleados_menores = set()
        empleados_menores_mujeres = set()
        empleados_menores_nuevos = set()
        empleados_mujeres_menoress_nuevos = set()
        empleados_menores_despedidos_hombres = set()
        empleados_menores_despedidos_mujeres = set()

        año_wizard = date_start.year
        # Inicia con los cálculos de las cinco filas
        data_rows = []
        asistencias_jornaleros_varones = {}
        asistencias_jornaleros_mujeres = {}
        ################################# Variables de los salarios de los supervisores ################################
        salario_total_supervisores_varones = 0
        salario_total_supervisores_mujeres = 0
        horas_trabajadas_supervisores_varones = 0
        horas_trabajadas_supervisores_mujeres = 0

        ##############################  Variables de los empleados que no son supervisores y son mensualeros ############
        salario_total_empleados_varones = 0
        salario_total_empleados_mujeres = 0
        horas_trabajdas_empleados_varones = 0
        horas_trabajdas_empleados_mujeres = 0

        ############################## Varialble para los jornaleros ###################################################
        salario_total_jornaleros_varones = 0
        salario_total_jornaleros_mujeres = 0

        ############################## variables para los menores de edad ############################################
        salario_total_menores_varones = 0
        salario_total_menores_mujeres = 0
        for payslip in payslip_records:
            employee_id = payslip.employee_id
            if not employee_id:
                continue  # Si no hay un empleado asociado, continúa con el siguiente registro
            # Verificamos si el empleado es un supervisor
            salario_supervisor = 0
            salario_empleado = 0
            salario_jornalero = 0
            salario_menores = 0

            #################### Lógica de conteo para empleados hombres y mujeres  supervisores###############
            # Lógica de conteo para empleados hombres y mujeres supervisores
            if employee_id.supervisor:
                # Supervisores activos (no despedidos durante el rango de fechas)
                if not employee_id.contract_id.date_end or employee_id.contract_id.date_end > wizard.end_date:
                    ###### Controlamos la cantidad de supervisores hombres #########
                    if employee_id.gender == 'male' and employee_id.id not in supervisores_contados:
                        supervisores_contados.add(employee_id.id)
                    ###### Controlamos la cantidad de supervisores mujeres  #########
                    elif employee_id.gender == 'female' and employee_id.id not in supervisores_contados_mujeres:
                        supervisores_contados_mujeres.add(employee_id.id)
                    ##### Controlamos el salario de los supervisores  #########
                    for line in payslip.line_ids:
                        if line.salary_rule_id.es_concepto_aguinaldo or line.salary_rule_id.beneficios or line.salary_rule_id.vacaciones or line.salary_rule_id.concepto_bonificaciones or line.salary_rule_id.salario_contrato:
                            salario_supervisor += line.total
                            if employee_id.gender == 'male':
                                salario_total_supervisores_varones += salario_supervisor
                            elif employee_id.gender == 'female':
                                salario_total_supervisores_mujeres += salario_supervisor

                # Supervisores nuevos ingresos (dentro del rango de fechas del wizard)
                if employee_id.contract_id.date_start and wizard.start_date <= employee_id.contract_id.date_start <= wizard.end_date:
                    if employee_id.gender == 'male' and employee_id.id not in empleados_supervisores_nuevos:
                        empleados_supervisores_nuevos.add(employee_id.id)
                    elif employee_id.gender == 'female' and employee_id.id not in empleados_supervisores_nuevos_mujeres:
                        empleados_supervisores_nuevos_mujeres.add(employee_id.id)

                # Supervisores con fecha de fin de contrato dentro del rango de fechas
                if employee_id.contract_id.date_end and wizard.start_date <= employee_id.contract_id.date_end <= wizard.end_date:
                    ###### Controlamos la cantidad de supervisores desvinculados #########
                    if employee_id.gender == 'male' and employee_id.id not in empleados_supervisores_despedidos_hombres:
                        empleados_supervisores_despedidos_hombres.add(employee_id.id)
                    elif employee_id.gender == 'female' and employee_id.id not in empleados_supervisores_despedidos_mujeres:
                        empleados_supervisores_despedidos_mujeres.add(employee_id.id)

            #################### Lógica de conteo para empleados hombres y mujeres ###############
            if not employee_id.supervisor and employee_id.contract_id.contract_type_id.es_mensualero:
                ###### Controlamos la cantidad de supervisores hombres #########
                if employee_id.gender == 'male' and employee_id.id not in empleados_hombres:
                    empleados_hombres.add(employee_id.id)
                    ######### Recorremos las entradas de trabajo para verificar que tenga ausencias #############
                    dias_restar = 0
                    for worked_day in payslip.worked_days_line_ids:
                        print("Ingresa  for worked_day in payslip.worked_days_line_ids ")
                        if worked_day.work_entry_type_id.es_ausencia_descontada:
                            dias_restar += worked_day.number_of_days
                        print("La cantidad de dias a restar es de :______________________", dias_restar)
                    if dias_restar >= 30:
                        horas_trabajadas_supervisores_varones = 0
                    else:
                        horas_trabajadas_supervisores_varones = (30 - (dias_restar))
                        print("la cantidad de horas trabajadas es de: ", horas_trabajadas_supervisores_mujeres)


                ######Controlamos la cantidad de supervisores mujeres  #########
                elif employee_id.gender == 'female' and employee_id.id not in empleados_mujeres:
                    empleados_mujeres.add(employee_id.id)
                    ######### Recorremos las entradas de trabajo para verificar que tenga ausencias #############
                    dias_restar = 0
                    for worked_day in payslip.worked_days_line_ids:
                        print("Ingresa  for worked_day in payslip.worked_days_line_ids ")
                        if worked_day.work_entry_type_id.es_ausencia_descontada:
                            dias_restar += worked_day.number_of_days
                        print("La cantidad de dias a restar es de :______________________", dias_restar)
                    if dias_restar >= 30:
                        horas_trabajadas_supervisores_mujeres = 0
                    else:
                        horas_trabajadas_supervisores_varones = (30 - (dias_restar))
                        print("la cantidad de horas trabajadas es de: ", horas_trabajadas_supervisores_varones)
                ##### calculamos el salario de los empleados #####
                for line in payslip.line_ids:
                    # Verificamos si la línea de nómina corresponde a alguna de las reglas con los atributos booleanos deseados
                    if line.salary_rule_id.es_concepto_aguinaldo or line.salary_rule_id.beneficios or line.salary_rule_id.vacaciones or line.salary_rule_id.concepto_bonificaciones or line.salary_rule_id.salario_contrato:
                        salario_empleado += line.total
                        # Sumamos al total general basado en el género del supervisor
                        if employee_id.gender == 'male':
                            salario_total_empleados_varones += salario_empleado
                        elif employee_id.gender == 'female':
                            salario_total_empleados_mujeres += salario_empleado
                if employee_id.contract_id.date_start.year == wizard.start_date.year not in empleados_hombres_nuevos not in empleados_mujeres_nuevos:
                    if employee_id.gender == 'male':
                        empleados_hombres_nuevos.add(employee_id.id)
                        ######### Recorremos las entradas de trabajo para verificar que tenga ausencias #############
                        dias_restar = 0
                        for worked_day in payslip.worked_days_line_ids:
                            if worked_day.work_entry_type_id.es_ausencia_descontada:
                                dias_restar += worked_day.number_of_days
                        if dias_restar >= 30:
                            horas_trabajdas_empleados_varones = 0
                        else:
                            horas_trabajdas_empleados_varones = (30 - (dias_restar))
                            print("la cantidad de horas trabajadas es de: ", horas_trabajdas_empleados_varones)
                    elif employee_id.gender == 'female':
                        print("Sumamos una empleado nueva")
                        empleados_mujeres_nuevos.add(employee_id.id)

                #################################################################################################################
                ######                      Controlamos la cantidad de empleados desvinculados                          #########
                #################################################################################################################
                if employee_id.contract_id.date_end and wizard.start_date <= employee_id.contract_id.date_end <= wizard.end_date:
                    ##################### supervisores desvinculados #############################
                    if employee_id.contract_id.date_end.year == wizard.start_date.year not in empleados_hombres_despedidos_hombres not in empleados_despedidos_mujeress:
                        if employee_id.gender == 'male':
                            empleados_hombres_despedidos_hombres.add(employee_id.id)
                        elif employee_id.gender == 'female':
                            empleados_despedidos_mujeress.add(employee_id.id)

            #################### Lógica de conteo para empleados hombres y mujeres  jornaleros###############
            if not employee_id.supervisor and employee_id.contract_id.contract_type_id.es_jornalero:
                # Buscar marcaciones de asistencia para el empleado jornalero en el rango de fechas
                marcaciones = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee_id.id),
                    ('check_in', '>=', wizard.start_date),
                    ('check_out', '<=', wizard.end_date)
                ])
                # Contar los registros de asistencia
                dias_asistidos = len(marcaciones)
                print("aaaaaaaaaaaaaaaaaaaaaaa", dias_asistidos)
                ###### Controlamos la cantidad de empleados hombres jornaleros #########
                if employee_id.gender == 'male' and employee_id.id not in empleados_jornaleros:
                    empleados_jornaleros.add(employee_id.id)
                    asistencias_jornaleros_varones[employee_id.id] = dias_asistidos

                ######Controlamos la cantidad de empleadas mujeres jornaleras  #########
                elif employee_id.gender == 'female' and employee_id.id not in empleados_mujeres_jornaleros:
                    empleados_mujeres_jornaleros.add(employee_id.id)
                    asistencias_jornaleros_mujeres[employee_id.id] = dias_asistidos

                ##### calculamos el salario de los empleados jornaleros #####
                for line in payslip.line_ids:
                    # Verificamos si la línea de nómina corresponde a alguna de las reglas con los atributos booleanos deseados
                    if line.salary_rule_id.es_concepto_aguinaldo or line.salary_rule_id.beneficios or line.salary_rule_id.vacaciones or line.salary_rule_id.concepto_bonificaciones or line.salary_rule_id.salario_contrato:
                        salario_jornalero += line.total
                        # Sumamos al total general basado en el género del empleado jornalero
                        if employee_id.gender == 'male':
                            salario_total_jornaleros_varones += salario_jornalero
                        elif employee_id.gender == 'female':
                            salario_total_jornaleros_mujeres += salario_jornalero
                if employee_id.contract_id.date_start.year == wizard.start_date.year not in empleados_jornaleros_nuevos not in empleados_mujeres_jornaleros_nuevos:
                    if employee_id.gender == 'male':
                        print("sumamos un empleado jornalero nuevo")
                        empleados_jornaleros_nuevos.add(employee_id.id)
                    elif employee_id.gender == 'female':
                        print("Sumamos una empleado jornalero nueva")
                        empleados_mujeres_jornaleros_nuevos.add(employee_id.id)
                #################################################################################################################
                ######                      Controlamos la cantidad de empleados desvinculados jornaleros                         #########
                #################################################################################################################
                if employee_id.contract_id.date_end and wizard.start_date <= employee_id.contract_id.date_end <= wizard.end_date:
                    ##################### supervisores desvinculados #############################
                    if employee_id.contract_id.date_end.year == wizard.start_date.year not in empleados_jornaleros_despedidos_hombres not in empleados_jornaleros_despedidos_mujeres:
                        if employee_id.gender == 'male':
                            empleados_jornaleros_despedidos_hombres.add(employee_id.id)
                        elif employee_id.gender == 'female':
                            empleados_jornaleros_despedidos_mujeres.add(employee_id.id)

            #################### Lógica de conteo para empleados hombres y mujeres  menores de edad ###############
            if not employee_id.supervisor and 0 < int(employee_id.employee_age) <= 18:
                ###### Controlamos la cantidad de empleados hombres menores #########
                if employee_id.gender == 'male' and employee_id.id not in empleados_menores:
                    empleados_menores.add(employee_id.id)
                    ######Controlamos la cantidad de empleadas mujeres menores  #########
                elif employee_id.gender == 'female' and employee_id.id not in empleados_menores_mujeres:
                    empleados_menores_mujeres.add(employee_id.id)
                ##### calculamos el salario de los empleados jornaleros #####
                for line in payslip.line_ids:
                    # Verificamos si la línea de nómina corresponde a alguna de las reglas con los atributos booleanos deseados
                    if line.salary_rule_id.es_concepto_aguinaldo or line.salary_rule_id.beneficios or line.salary_rule_id.vacaciones or line.salary_rule_id.concepto_bonificaciones or line.salary_rule_id.salario_contrato:
                        salario_menores += line.total
                        # Sumamos al total general basado en el género del empleado jornalero
                        if employee_id.gender == 'male':
                            salario_total_menores_varones += salario_menores
                        elif employee_id.gender == 'female':
                            salario_total_menores_mujeres += salario_menores
                if employee_id.contract_id.date_start.year == wizard.start_date.year not in empleados_menores_nuevos not in empleados_mujeres_menoress_nuevos:
                    if employee_id.gender == 'male':
                        empleados_menores_nuevos.add(employee_id.id)
                    elif employee_id.gender == 'female':
                        empleados_mujeres_menoress_nuevos.add(employee_id.id)
                #################################################################################################################
                ######                      Controlamos la cantidad de empleados desvinculados jornaleros                         #########
                #################################################################################################################
                if employee_id.contract_id.date_end and wizard.start_date <= employee_id.contract_id.date_end <= wizard.end_date:
                    ##################### supervisores desvinculados #############################
                    if employee_id.contract_id.date_end.year == wizard.start_date.year not in empleados_menores_despedidos_hombres not in empleados_menores_despedidos_mujeres:
                        if employee_id.gender == 'male':
                            empleados_menores_despedidos_hombres.add(employee_id.id)
                        elif employee_id.gender == 'female':
                            empleados_menores_despedidos_mujeres.add(employee_id.id)

            # Definir el año para el cual deseas calcular los feriados
            año_wizard = wizard.start_date.year  # Reemplaza con el año deseado
            # Inicializar una lista para almacenar todos los feriados del año
            feriados_totales = []
            # Bucle a través de todos los meses del año (de enero a diciembre)
            for mes in range(1, 13):
                # Calcular la fecha de inicio y fin del mes actual
                fecha_inicio_mes = date(año_wizard, mes, 1)
                ultimo_dia_mes = calendar.monthrange(año_wizard, mes)[1]
                fecha_fin_mes = date(año_wizard, mes, ultimo_dia_mes)
                feriados_mes = self.env['resource.calendar.leaves'].search([
                    ('date_from', '>=', fecha_inicio_mes),
                    ('date_to', '<=', fecha_fin_mes),
                    ('resource_id', '=', False),
                ])
                # Agregar los feriados del mes actual a la lista total de feriados
                feriados_totales.extend(feriados_mes)

            for feriado in feriados_totales:
                print("************  Nombre del feriado  ****************", feriado.name)

            cantidad_feriados_totales = len(feriados_totales)
            print("___________________________________________ LA CANTIDAD DE FERIADOS ES DE ",
                  cantidad_feriados_totales)

        # ----------------------      INICIO DE TOTALIZADORES DE LOS SUPERVISORES     ----------------------------------#
        total_supervisores = len(supervisores_contados)
        total_supervisores_mujeres = len(supervisores_contados_mujeres)
        total_supervisores_nuevos_ano = len(empleados_supervisores_nuevos)
        total_supervisores_nuevos_ano_mujeres = len(empleados_supervisores_nuevos_mujeres)
        total_supervisores_desvinculados_nuevos_ano_hombre = len(empleados_supervisores_despedidos_hombres)
        total_supervisores_desvinculados_nuevos_ano_mujer = len(empleados_supervisores_despedidos_mujeres)
        total_salarios_supervisores_hombres = salario_total_supervisores_varones
        total_salarios_supervisores_muejeres = salario_total_supervisores_mujeres
        # ----------------------      FIN DE TOTALIZADORES DE LOS SUPERVISORES        ----------------------------------#

        # ----------------------      INICIO DE TOTALIZADORES EMPLEADOS MENSUALEROS    ---------------------------------#
        total_empleados = len(empleados_hombres)
        total_empleados_mujeres = len(empleados_mujeres)
        total_empleados_nuevos_varones = len(empleados_hombres_nuevos)
        total_empleados_nuevos_mujeres = len(empleados_mujeres_nuevos)
        total_salario_empleados_varones = salario_total_empleados_varones
        total_salario_empleados_mujeres = salario_total_empleados_mujeres
        total_empleados_desvinculados_varones = len(empleados_hombres_despedidos_hombres)
        total_empleados_desvinculados_mujeres = len(empleados_despedidos_mujeress)
        # ---------------------       FIN DE TOTALIZADORES DE LOS EMPLEADOS MENSUALEROS   ------------------------------#

        # ----------------------      INICIO DE TOTALIZADORES EMPLEADOS JORNALEROS    ---------------------------------#
        total_jornaleros = len(empleados_jornaleros)
        total_mujeres_jornaleros = len(empleados_mujeres_jornaleros)
        total_salario_jornalero_varones = salario_total_jornaleros_varones
        total_salario_jornalero_mujeres = salario_total_jornaleros_mujeres
        total_empleados_jornaleros_nuevos = len(empleados_jornaleros_nuevos)
        total_empleados_jornaleros_nuevos_mujeres = len(empleados_mujeres_jornaleros_nuevos)
        total_empleados_jornaleros_desvinculados = len(empleados_jornaleros_despedidos_hombres)
        total_empleados_jornaleros_desvinculados_mujeres = len(empleados_jornaleros_despedidos_mujeres)
        # Sumarizar asistencias de jornaleros varones y mujeres
        total_asistencias_jornaleros_varones = sum(asistencias_jornaleros_varones.values())
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", total_asistencias_jornaleros_varones)
        total_asistencias_jornaleros_mujeres = sum(asistencias_jornaleros_mujeres.values())

        # ---------------------       FIN DE TOTALIZADORES DE LOS EMPLEADOS MENSUALEROS   ------------------------------#

        # ----------------------      INICIO DE TOTALIZADORES EMPLEADOS MENORES DE EDAD    ---------------------------------#

        total_menores_varones = len(empleados_menores)
        total_menores_muejeres = len(empleados_menores_mujeres)
        total_salario_salario_menores_varones = salario_total_menores_varones
        total_salario_salario_menores_mujeres = salario_total_menores_mujeres
        total_empleados_menores_nuevos = len(empleados_menores_nuevos)
        total_empleados_menores_nuevos_mujeres = len(empleados_mujeres_menoress_nuevos)
        total_empleados_menores_desvinculados = len(empleados_menores_despedidos_hombres)
        total_empleados_menores_desvinculados_mujeres = len(empleados_menores_despedidos_mujeres)
        # ----------------------      FIN DE TOTALIZADORES EMPLEADOS MENORES DE EDAD    ---------------------------------#

        data_rows.append([payslip.company_id.company_registry,
                          año_wizard,
                          total_supervisores + total_supervisores_desvinculados_nuevos_ano_hombre,
                          total_supervisores_mujeres + total_supervisores_desvinculados_nuevos_ano_mujer,
                          total_empleados,
                          total_empleados_mujeres,
                          total_jornaleros,
                          total_mujeres_jornaleros,
                          total_menores_varones,
                          total_menores_muejeres,
                          1])
        ###################################### Fila 2: filas de horas trabajadas ########################################
        data_rows.append([payslip.company_id.company_registry, año_wizard,
                          (horas_trabajadas_supervisores_varones + cantidad_feriados_totales) * 8,
                          (horas_trabajadas_supervisores_mujeres + cantidad_feriados_totales) * 8,
                          (horas_trabajdas_empleados_varones + cantidad_feriados_totales) * 8,
                          (horas_trabajdas_empleados_mujeres + cantidad_feriados_totales) * 8,
                          total_asistencias_jornaleros_varones, total_asistencias_jornaleros_mujeres, 0, 0, 2])

        ###################################### Fila 3: filas de salarios        ########################################
        data_rows.append([payslip.company_id.company_registry, año_wizard, total_salarios_supervisores_hombres,
                          total_salarios_supervisores_muejeres, total_salario_empleados_varones,
                          total_salario_empleados_mujeres, total_salario_jornalero_varones,
                          total_salario_jornalero_mujeres, total_salario_salario_menores_varones,
                          total_salario_salario_menores_mujeres, 3])
        # Fila 4: Fila de los ingresos del año
        data_rows.append([payslip.company_id.company_registry, año_wizard, total_supervisores_nuevos_ano,
                          total_supervisores_nuevos_ano_mujeres, total_empleados_nuevos_varones,
                          total_empleados_nuevos_mujeres, total_empleados_jornaleros_nuevos,
                          total_empleados_jornaleros_nuevos_mujeres, total_empleados_menores_nuevos,
                          total_empleados_menores_nuevos_mujeres, 4])
        # Fila 5: FILA DE LAS DESVINCULACIONES
        data_rows.append(
            [payslip.company_id.company_registry, año_wizard, total_supervisores_desvinculados_nuevos_ano_hombre,
             total_supervisores_desvinculados_nuevos_ano_mujer, total_empleados_desvinculados_varones,
             total_empleados_desvinculados_mujeres, total_empleados_jornaleros_desvinculados,
             total_empleados_jornaleros_desvinculados_mujeres, total_empleados_menores_desvinculados,
             total_empleados_menores_desvinculados_mujeres, 5])
        # Asegúrate de que solo tienes cinco filas de datos
        data_rows = data_rows[:5]
        # Escribe los datos en la hoja de cálculo
        row_index = 1  # Empieza después de la fila de encabezados

        for row_data in data_rows:
            for col_index, value in enumerate(row_data):
                sheet.write(row_index, col_index, value, formato_contenido)
            row_index += 1

