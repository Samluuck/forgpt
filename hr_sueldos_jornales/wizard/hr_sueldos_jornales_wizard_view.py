import logging
import calendar
from odoo import api, fields, models, tools, _
from datetime import date, timedelta , datetime
from calendar import monthrange
from odoo.exceptions import ValidationError
from collections import defaultdict
_logger = logging.getLogger(__name__)


class HrPayRollWizard(models.TransientModel):

    _name = "hr_sueldos_jornales_wizard_view"
    start_date = fields.Date(string="Fecha Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    type_reports = fields.Selection([('6', 'Registros de Sueldos y Jornales')],string="Reporte de:", default='6')
    formato_importacion = fields.Boolean(string="Formato Anual", help="Seleccione el formato deseado")

    def check_report_syj(self):
        data = {}
        data['form'] = self.read(['type_reports'])[0]
        return self._print_report(data)
    def _print_report(self, data):
        data['form'].update(
            self.read(['start_date', 'end_date', 'type_reports'])[0])
        return self.env.ref(
            'hr_sueldos_jornales.hr_sueldos_jornales_report_action'
        ).report_action(self, data)

class ReportPayRollXLSXWizard(models.AbstractModel):
    _name = 'report.hr_sueldos_jornales.payroll_report_xlsx'
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

    def generate_xlsx_report(self, workbook, data, wizard):
        _logger.debug('Este es un mensaje de aviso que ha ingresado a generate_xlsx_report')
        # Obteniendo los datos desde el wizard
        date_start = wizard.start_date
        date_end = wizard.end_date
        company_name = self.env.user.company_id.name #nombre de la compañia
        company_name_calle = self.env.user.company_id.street #calle de la compañia
        correo_empresa = self.env.user.company_id.email #correo de la compañia
        telefono_empresa = self.env.user.company_id.phone #tel de la compañia
        web= self.env.user.company_id.website #sitio de la compañia
        sheet = workbook.add_worksheet()
        ################## Definición de formatos #####################3
        merge_format_head = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        bold_center = workbook.add_format({
            'align': 'center',
            'bold': True,
            'font_size': 8,
        })
        bold_left = workbook.add_format({
            'align': 'left',
            'font_size': 10,
        })
        titulo = workbook.add_format({
            'align': 'center',
            'font_size': 15,
            'bold': True,
        })
        contenido = workbook.add_format({
            'align': 'center',
            'font_size': 11,
            'bold': True,
            'font_name': 'Ubuntu'
        })
        contenido_fin_semana = workbook.add_format({
            'align': 'center',
            'font_size': 11,
            'bold': True,
        })
        contenido_2 = workbook.add_format({
            'align': 'center',
            'font_size': 10,
            'color': 'red',
            'bold': True,
        })
        cabecera_no_importacion = workbook.add_format({
            'align': 'center',
            'font_size': 12,
            'bold': True,
        })
        header_sub_format = workbook.add_format({
            'border': 1,
            'bg_color': '#FFFFFF',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 10,
        })
        # Estilo para las cabeceras "Nº de Orden", "NOMBRE Y APELLIDO", y "Nº C.I."
        header_format_1 = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 12,
        })
        #  Estilo para los números del 1 al 31.
        header_format_2 = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size':8,
        })
        # 3. Estilo para "Forma de Pago", "Importe Unitario" y "Días de Trabajo".
        header_format_3 = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 10,
        })
        sub_headers = [
            'Forma de Pago',
            'Importe Unitario',
            'Días de Trabajo',
        ]
        if not wizard.formato_importacion:
            _logger.debug('Este es un mensaje de aviso que el usuario elige imprimir el reporte en formaTO ')
            ################## Para que aparezca la imagen hay que poner el camino completo de la imagen, a tener en cuenta para instalaciones en los clientes #################################3333
            sheet.insert_image('A1', 'documenta/hr_sueldos_jornales/static/img/img.jpeg', {'x_scale': 0.9, 'y_scale': 0.9})
            # 4. Información de la empresa y otros encabezados
            sheet.merge_range('B5:I5', 'VICE MINISTERIO DE TRABAJO Y SEGURIDAD SOCIAL', merge_format_head)
            sheet.merge_range('B6:I6', 'DIRECCION GENERAL DEL TRABAJO', merge_format_head)
            ############################### encabezados ####################################333
            sheet.write('M1', 'Sueldos y Jornales', titulo)
            sheet.write('K2', 'AÑO:', bold_left)
            sheet.write('L2', str(date_start.year), bold_left)
            sheet.write('K3', 'MES:', bold_left)
            month_name = calendar.month_name[date_start.month].capitalize()
            sheet.write('L3', month_name, bold_left)
            sheet.write('O2', 'EMPLEADOR:' , bold_left)
            sheet.write('P2', company_name , bold_left)
            sheet.write('AF2', 'N° PATRONAL MJT:', bold_left)
            sheet.write('AF3', 'N° PATRONAL IPS:', bold_left)
            sheet.write('AF4', 'RUC:', bold_left)
            sheet.write('AF5', 'TELEFONO:', bold_left)
            sheet.write('AG5', telefono_empresa , bold_left)
            sheet.write('AF6', 'Correo electrónico:', bold_left)
            sheet.write('AG6', correo_empresa , bold_left)
            sheet.write('AF7', 'Página Web:', bold_left)
            sheet.write('AG7', web, bold_left)
            sheet.write('O3', 'RAZON SOCIAL: Empresa S.A.', bold_left)
            sheet.write('O4', 'ACTIVIDAD : Importación', bold_left)
            sheet.write('O5', 'DOMICILIO:', bold_left)
            sheet.write('O6', 'DEPARTAMENTO:', bold_left)
            sheet.write('O7', 'LOCALIDAD:', bold_left)
            sheet.merge_range('AI8:AJ7', 'SALARIO', bold_center)  # Asume que AC es la columna de "Forma de Pago"
            sheet.merge_range('AK8:AL7', 'TOTAL', bold_center)
            sheet.merge_range('AM8:AO7', 'HORAS EXTRAS', bold_center)
            sheet.merge_range('AP8:AS7', 'B E N E F I C I O S   S O C I A L E S ', bold_center)
            sheet.merge_range('AT8:AT7', 'TOTAL GENERAL', bold_center)
            column_headers_1 = ['Nº de Orden', 'NOMBRE Y APELLIDO', 'Nº C.I.']
            column_headers_2 = [str(i) for i in range(1, 32)]
            column_headers_3 = ['Forma de Pago', 'Importe Unitario', 'Días de Trabajo' ,'Horas Trabajadas','Importe','50%', '100%','Vacaciones','Bonificación Familiar','Aguinaldo','Otros Beneficios'
                                                                                                               ]

            row = 8
            # Posicionar las cabeceras
            col_num = 0  # Esta variable nos ayuda a saber en qué columna estamos escribiendo
            # Colocar subcabeceras
            for col_num, sub_header in enumerate(sub_headers):
                sheet.write(8, col_num, sub_header, header_sub_format)
            for col_num, header in enumerate(column_headers_1):
                sheet.write(row, col_num, header, header_format_1)
            # Ajustar el ancho de la columna "NOMBRE Y APELLIDO"
            sheet.set_column(1, 1, 30)  # Ajustamos el ancho de la columna a 30
            sheet.set_column(2, 2, 10)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(3, 33, 3)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(34, 34, 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(35, 35, 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(36, 36, 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(37, 37, 18)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(41, 41, 18)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(42, 42 , 18)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(43, 43 , 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(44, 44 , 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(45, 45 , 15)  # Ajusta el ancho de la columna "Nº
            sheet.set_column(46, 46 , 20)  # Ajusta el ancho de la columna "Nº

            for col_num, header in enumerate(column_headers_2, start=len(column_headers_1)):
                sheet.write(row, col_num, header, header_format_2)

            for col_num, header in enumerate(column_headers_3, start=len(column_headers_1) + len(column_headers_2)):
                sheet.write(row, col_num, header, header_format_3)

            empleados_agregados = set()  # Inicializa un conjunto vacío para mantener un registro de los IDs de empleados agregados.

            # Filtrando los registros de nómina por el rango de fechas
            payslip_records = self.env['hr.payslip'].search([('date_from', '>=', date_start),('date_to', '<=', date_end)])  # Aquí podrías agregar criterios específicos si solo deseas algunas nóminas
            row_num = 10  # Esta es la fila en la que empezarás a escribir los datos. Ajusta según tus necesidades.
            c = 1  # Asumo que quieres empezar desde 1. Ajusta según sea necesario.
            for payslip in payslip_records:
                employee_id = payslip.employee_id.identification_id  # Obtén el ID del empleado de la nómina.
                if employee_id not in empleados_agregados:  # Verifica si este empleado ya ha sido procesado.
                    empleados_agregados.add(
                        employee_id)  # Agrega el ID del empleado al conjunto para no procesarlo nuevamente.

                    col_num = 0  # Comenzamos en la primera columna
                    # Escribir datos básicos del empleado
                    sheet.write(row_num, col_num, c, contenido)
                    c += 1
                    col_num += 1
                    sheet.write(row_num, col_num, payslip.employee_id.name, contenido)
                    col_num += 1
                    sheet.write(row_num, col_num, payslip.employee_id.identification_id, contenido)
                    # Obtener las ausencias del empleado durante el mes del payslip.
                    leaves = self.env['hr.leave'].search([
                        ('employee_id', '=', payslip.employee_id.id),
                        ('date_from', '>=', date_start),
                        ('date_to', '<=', date_end)
                    ])
                    # Crear un diccionario para mapear cada día a su razón de ausencia
                    leave_days = {}
                    for leave in leaves:
                        start = max(leave.date_from.date(), date_start)  # Convierte datetime a date antes de comparar
                        end = min(leave.date_to.date(), date_end)  # Convierte datetime a date antes de comparar
                        current_date = start
                        while current_date <= end:
                            day = current_date.day
                            leave_days[day] = 'A'  # Ahora simplemente colocamos 'A' para ausencia
                            current_date += timedelta(days=1)
                    # Verificar ausencias y escribir valores correspondientes
                    year=date_start.year
                    month=date_start.month
                    cantidad_domingos = 0
                    cantidad_sabado = 0
                    cantidad_feriados = 0
                    for day in range(1, 32):
                        current_date = date(year, month, day)
                        leave = self.env['hr.leave'].search([
                            ('employee_id', '=', payslip.employee_id.id),
                            ('date_from', '<=', current_date),
                            ('date_to', '>=', current_date)
                        ], limit=1)# Solo necesitamos encontrar al menos una ausencia para ese día
                        #Buscar los días feriados en enero de ese año
                        feriados_por_mes = self.env['resource.calendar.leaves'].search([
                            ('date_from', '>=', current_date),  # Primer día de enero
                            ('date_to', '<=', current_date),  # Último día de enero
                            ('resource_id', '=', False),  # Ausencias que no están asociadas a un recurso específico (Esto se hace para que tome solo los feriados)
                        ])

                        vacaciones = self.env['hr.leave'].search([
                            ('employee_id', '=', payslip.employee_id.id),
                            ('date_from', '<=', current_date),
                            ('date_to', '>=', current_date),
                            ('state', '=', 'validate'),  # Asumiendo que solo las vacaciones validadas cuentan
                            ('holiday_status_id.es_vacacion', '=', True),
                            # Accede al campo relacionado 'es_vacacion' en 'hr.leave.type'
                        ], limit=1)

                        col_num += 1

                        # Verificar si el día es sábado o domingo
                        if current_date.weekday() == 6 and not leave and not vacaciones:
                            print("Es domingo por ende lleva /")
                            cantidad_domingos =cantidad_domingos+ 1
                            sheet.write(row_num, col_num, '/',contenido_fin_semana)
                            print("Cantidad de Domingos",cantidad_domingos)

                        elif current_date.weekday() == 5 and not leave and not vacaciones:
                            cantidad_sabado += 1
                            sheet.write(row_num, col_num, '/',contenido_fin_semana)
                            print("Cantidad de sabados",cantidad_sabado)
                        elif leave and not vacaciones:  # Si hay una ausencia para ese día
                            print("------------------------------> Es una ausencia")
                            sheet.write(row_num, col_num, 'A',contenido_2)

                        elif feriados_por_mes:
                            print("Es feriado <------------------------------")
                            cantidad_feriados+=1
                            sheet.write(row_num, col_num, 'F',contenido_fin_semana)

                        elif vacaciones:
                            sheet.write(row_num, col_num, 'V',contenido_fin_semana)

                        else:
                            sheet.write(row_num, col_num, '8',contenido)
                    # Incrementa el contador de columna para pasar a la columna siguiente
                    col_num += 1

                    print("el empleado es *******************************",payslip.contract_id.structure_type_id.default_schedule_pay)
                    sheet.write(row_num, col_num, 'Mensualero' if payslip.contract_id.structure_type_id.default_schedule_pay == 'monthly' else 'Jornalero', contenido)
                    # Incrementa el contador de columna para pasar a la columna siguiente
                    col_num += 1
                    contrato= round(payslip.contract_id.wage)
                    importe_unitario = round(contrato/30)
                    sheet.write(row_num, col_num, importe_unitario, contenido)
                    # Incrementa el contador de columna para pasar a la columna siguiente
                    col_num += 1
                    total_dias_trabajados = 0
                    for worked_day in payslip.worked_days_line_ids:
                        if worked_day.code in ('VAC', 'MAT', 'OUT', 'LEAVE90', 'LEAVE110'):
                            total_dias_trabajados += worked_day.number_of_days


                    dias_trabajados_final = 30 - (total_dias_trabajados+cantidad_sabado+cantidad_domingos+cantidad_feriados)  # Calcula días trabajados fuera del bucle
                    sheet.write(row_num, col_num, dias_trabajados_final, contenido)

                    ############# Incrementa el contador de columna para pasar a la columna siguiente #################
                    col_num += 1

                    sheet.write(row_num, col_num, dias_trabajados_final*8, contenido)
                    col_num += 1

                    sheet.write(row_num, col_num, contrato, contenido)
                    col_num += 1

                    ################### columna correspondiente a el 50% ##############################################
                    sheet.write(row_num, col_num, 0, contenido)
                    col_num+=1

                    ###################  columna correspondiente a el 100% ############################################
                    sheet.write(row_num, col_num, 0, contenido)
                    col_num+=1
                    monto_vacaciones=0
                    bonificacion_familiar=0
                    aguinaldo_proporcional= 0
                    beneficios = 0
                    salario_basico_reporte=0
                    for line in payslip.line_ids:
                        ##################   columna de vacaciones  ########################################################
                        if line.salary_rule_id.vacaciones:
                            monto_vacaciones +=line.total
                        ############### columna de bonificacion familiar ##################################################
                        if line.salary_rule_id.bonificaciones:
                            bonificacion_familiar += line.total
                        #####################     columna de aguinaldo    ##################################################
                        if line.salary_rule_id.aguinaldo_proporcional_desvinculacion:
                            aguinaldo_proporcional +=line.total
                        ###################     columna de beneficios    ###################################################
                        if line.salary_rule_id.beneficios:
                            beneficios +=line.total

                        ###################     columna de beneficios    ###################################################
                        if line.salary_rule_id.salario_basico:
                            salario_basico_reporte +=line.total

                    sheet.write(row_num, col_num, monto_vacaciones, contenido)#VACACIONES
                    col_num+=1
                    sheet.write(row_num, col_num, bonificacion_familiar, contenido)#BONIFICACION FAMILIAR
                    col_num+=1
                    sheet.write(row_num, col_num, aguinaldo_proporcional, contenido)#Aguinaldo
                    col_num+=1
                    sheet.write(row_num, col_num, beneficios, contenido)#Beneficios
                    col_num+=1
                    sheet.write(row_num, col_num,aguinaldo_proporcional+ beneficios+monto_vacaciones+bonificacion_familiar+beneficios+salario_basico_reporte, contenido)  # Beneficios
                    col_num += 1

                    row_num += 1  # Mover a la siguiente fila para la próxima nómina
        else:
            _logger.debug('El usuario elige imprimir el reporte en formato de importación')

            columnas = [
                "Nropatronal", "documento", "formadepago", "importeunitario",
                "h_ene", "s_ene", "h_feb", "s_feb", "h_mar", "s_mar",
                "h_abr", "s_abr", "h_may", "s_may", "h_jun", "s_jun",
                "h_jul", "s_jul", "h_ago", "s_ago", "h_set", "s_set",
                "h_oct", "s_oct", "h_nov", "s_nov", "h_dic", "s_dic",
                "h_50", "s_50", "h_100", "s_100",
                "Aguinaldo", "Beneficios", "Bonificaciones", "Vacaciones",
                "total_h", "total_s", "totalgeneral"
            ]
            for col, nombre in enumerate(columnas):
             sheet.write(0, col, nombre, cabecera_no_importacion)

            



            def agregar_punto_de_miles(numero):
             numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
             return numero_con_punto

            payslip_records = self.env['hr.payslip'].search(
                [('date_from', '>=', wizard.start_date), ('date_to', '<=', wizard.end_date)])
            empleados_data = {}
            meses = {
                        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
                        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
                    }
            year=date_start.year
            for payslip in payslip_records:
             employee_id = payslip.employee_id.id

             if employee_id not in empleados_data:
                 if payslip.contract_id.contract_type_id.es_mensualero is None:
                    raise ValidationError(f"El empleado {payslip.employee_id.name} tiene un tipo de contrato inválido.")
                 empleados_data[employee_id] = {
                     'id': employee_id,
                     'nro_patronal': payslip.company_id.company_registry,
                     'documento': payslip.employee_id.identification_id,
                     'forma_de_pago': 'M' if payslip.contract_id.contract_type_id.es_mensualero else 'J',
                     'importe_unitario': round(payslip.contract_id.wage / 30) if payslip.contract_id.wage else 0,

                     # Generar horas y salarios por mes dinámicamente
                     **{f"hora_{mes}": 0 for mes in meses},
                     **{f"salario_basico_{mes}": 0 for mes in meses},

                     'h50': 0, 's50': 0,
                     'h100': 0, 's100': 0,
                     'aguinaldo': 0,
                     'beneficios': 0,
                     'bonificaciones': 0,
                     'vacaciones': 0,
                     'total_h': 0,
                     'total_s': 0,
                     'totalgeneral': 0,
                 }



        #Recorrer por empleado                                                    
        for emp in empleados_data:
            

            # Traer todos los payslips del año para ese empleado una sola vez
            payslips_empleado = self.env['hr.payslip'].search([
                ('employee_id', '=', emp),
                ('date_from', '>=', date(year, 1, 1)),
                ('date_to', '<=', date(year, 12, 31)),
                ('struct_id.dias_trabajados', '=', True)
            ])
            


            # Cargar por mes
            payslips_por_mes = defaultdict(list)
            for payslip in payslips_empleado:
                mes_payslip = payslip.date_from.month #Extrae el mes 
                payslips_por_mes[mes_payslip].append(payslip)#si no existe crea uno 


            #Recorre los meses
            for mes_num in range(1, 13):
                #Funcion que retorna el ultimo dia del mes                
                fin_mes = calendar.monthrange(year, mes_num)[1]
                mes_str = meses[mes_num]
                dias_restar = 0
                sueldo_mes=0
                aguinaldo=0
                s_100=0
                s_50=0
                # Feriados del mes
                feriados_mes = self.env['resource.calendar.leaves'].search([
                    ('date_from', '>=', date(year, mes_num, 1)),
                    ('date_to', '<=', date(year, mes_num, fin_mes)),
                    ('resource_id', '=', False)
                ])
                #Saca el numero de feriados 
                feriados = len(feriados_mes)
                if mes_num == 12:
                    print("Diciembre")
                    aguinaldo=sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.aguinaldo)
                        for payslip in payslips_por_mes[mes_num]
                        
                    )

                #Trae las bonificaciones 
                bonificaciones=sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.concepto_bonificaciones)
                        for payslip in payslips_por_mes[mes_num]
                        
                    )   
                #Trae los beneficios
                beneficios=sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.beneficios)
                        for payslip in payslips_por_mes[mes_num]
                        
                    )  
                #Trae las vacaciones
                vacaciones =sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.vacaciones           )
                        for payslip in payslips_por_mes[mes_num]
                        
                    )  
                s_50 = sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.h_50           )
                        for payslip in payslips_por_mes[mes_num]
                        
                    ) 
                s_100 = sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.h_100          )
                        for payslip in payslips_por_mes[mes_num]
                        
                    )   
                 #Si no son mensualeros
                if empleados_data[emp]['forma_de_pago'] != "M": 

                    #Busca las asistencias de ese empleado en el mes
                    asistencia = self.env['hr.attendance'].search([  
                        ('employee_id', '=', emp),
                        ('check_in','>=',date(year, mes_num,1)),
                        ('check_out','<=',date(year, mes_num,fin_mes))
                    ])

                    #Extrae las horas y le da un rendondeo de dos decimales
                    horas = round(sum(asistencia.mapped('worked_hours')),2) 

                    #Extrae y suma los pagos que recibio  en el mes 
                    sueldo_mes += sum( sum( line.total for line in payslip.line_ids if line.salary_rule_id.code in ['GROOS', 'BRUTO'])
                        for payslip in payslips_por_mes[mes_num]
                    )
                    
                else:

                    #Para mensualeros busca las ausencias registradas en ese mes 
                    for payslip in payslips_por_mes[ mes_num ]:
                        for wd in payslip.worked_days_line_ids:
                            if wd.work_entry_type_id.es_ausencia_descontada:
                                dias_restar += wd.number_of_days
                    #Le resta las ausencias y las vacaciones 
                    horas = 0 if dias_restar >= fin_mes else (24 - (dias_restar + feriados)) * 8
                    sueldo_mes += sum(
                        sum(line.total for line in payslip.line_ids if line.salary_rule_id.code in ['GROOS', 'BRUTO'])
                        for payslip in payslips_por_mes[mes_num]
                    )


                # if sueldo_mes < 0:
                #     raise ValidationError(f"El salario del empleado {payslip.employee_id.name} en {mes_str} es negativo ({sueldo_mes}). Verifica las reglas salariales.")

                #Carga las horas y el sueldo al final
                empleados_data[emp][f'hora_{mes_str}'] = horas
                empleados_data[emp]['total_h'] += horas
                #Carga los salarios 
                empleados_data[emp][f'salario_basico_{mes_str}'] = agregar_punto_de_miles(sueldo_mes)
                empleados_data[emp]['total_s'] += (sueldo_mes - aguinaldo - bonificaciones - beneficios - vacaciones)
                empleados_data[emp]['aguinaldo'] += (aguinaldo) 
                empleados_data[emp]['bonificaciones'] += (bonificaciones ) 
                empleados_data[emp]['beneficios']+= (beneficios )  
                empleados_data[emp]['vacaciones'] += (vacaciones )  
                empleados_data[emp]['s50'] += s_50 
                empleados_data[emp]['s100']+= s_100  
                empleados_data[emp]['totalgeneral'] += sueldo_mes



                 
               

        for row_num, (employee_id, employee_data) in enumerate(empleados_data.items(), start=1):
            sheet.write(row_num, 0, employee_data['nro_patronal'])
            sheet.write(row_num, 1, employee_data['documento'])
            sheet.write(row_num, 2, employee_data['forma_de_pago'])
            sheet.write(row_num, 3, employee_data['importe_unitario'])

            for i, mes in enumerate(meses.values()):
                sheet.write(row_num, 4 + i * 2, employee_data[f"hora_{mes}"])
                sheet.write(row_num, 5 + i * 2, employee_data[f"salario_basico_{mes}"])

            sheet.write(row_num, 28, employee_data['h50'])
            sheet.write(row_num, 29, agregar_punto_de_miles(employee_data['s50']))
            sheet.write(row_num, 30, employee_data['h100'])
            sheet.write(row_num, 31, agregar_punto_de_miles(employee_data['s100']))
            sheet.write(row_num, 32, agregar_punto_de_miles(employee_data['aguinaldo']))
            sheet.write(row_num, 33, agregar_punto_de_miles(employee_data['beneficios']))
            sheet.write(row_num, 34, agregar_punto_de_miles(employee_data['bonificaciones']))
            sheet.write(row_num, 35, agregar_punto_de_miles(employee_data['vacaciones']))
            sheet.write(row_num, 36, agregar_punto_de_miles(employee_data['total_h']))
            sheet.write(row_num, 37, agregar_punto_de_miles(employee_data['total_s']))
            sheet.write(row_num, 38, agregar_punto_de_miles(employee_data['totalgeneral']))