import logging
import calendar
from odoo import api, fields, models, tools, _
from datetime import date, timedelta

_logger = logging.getLogger(__name__)




class HrPayRollWizard(models.TransientModel):

    _name = "hr_empleados_obreros_wizard_view"
    start_date = fields.Date(string="Fecha Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    type_reports = fields.Selection([('6', 'Registros de Sueldos y Jornales')],string="Reporte de:", default='6')
    formato_importacion = fields.Boolean(string="Formato Importación", help="Seleccione el formato deseado")

    def check_report_hr_empleados_obreros(self):
        data = {}
        data['form'] = self.read(['type_reports'])[0]
        return self._print_report(data)
    def _print_report(self, data):
        data['form'].update(
            self.read(['start_date', 'end_date', 'type_reports'])[0])
        return self.env.ref(
            'hr_empleados_obreros.hr_empleados_obreros_report_action'
        ).report_action(self, data)

class ReportPayRollXLSXWizard(models.AbstractModel):
    _name = 'report.hr_empleados_obreros.payroll_report_xlsx'
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
        ruc= self.env.user.company_id.ruc #sitio de la compañia
        domicilio= self.env.user.company_id.street
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

        # Definir los formatos para la cabecera
        header_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bg_color': '#FFFFFF',
            'font_size': 10,
        })
        if not wizard.formato_importacion:
            _logger.debug('Este es un mensaje de aviso que el usuario elige imprimir el reporte en formaTO ')
            ################## Para que aparezca la imagen hay que poner el camino completo de la imagen, a tener en cuenta para instalaciones en los clientes #################################3333
            sheet.insert_image('A1', 'documenta/hr_sueldos_jornales/static/img/img.jpeg', {'x_scale': 0.9, 'y_scale': 0.9})
            # 4. Información de la empresa y otros encabezados
            sheet.merge_range('B5:I5', 'VICE MINISTERIO DE TRABAJO Y SEGURIDAD SOCIAL', merge_format_head)
            sheet.merge_range('B6:I6', 'DIRECCION GENERAL DEL TRABAJO', merge_format_head)
            ############################### encabezados ####################################333
            sheet.write('M1', ' Empleados y Obreros', titulo)
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
            sheet.write('O3', 'RAZON SOCIAL: ', bold_left)
            sheet.write('O4', 'ACTIVIDAD : ', bold_left)
            sheet.write('O5', 'DOMICILIO:', bold_left)
            sheet.write('P5', domicilio, bold_left)
            sheet.write('O6', 'DEPARTAMENTO:', bold_left)
            sheet.write('O7', 'LOCALIDAD:', bold_left)
            sheet.write('O7', 'LOCALIDAD:', bold_left)

            # Escribir las cabeceras de las columnas
            sheet.write('A10', 'N°', header_format)
            sheet.write('B10', 'Apellidos', header_format)
            sheet.write('C10', 'Nombres', header_format)
            sheet.write('D10', 'Domicilio', header_format)
            sheet.write('E10', 'Nacionalidad', header_format)
            sheet.write('F10', 'C.I. N°', header_format)
            sheet.write('G10', 'Edad', header_format)
            sheet.write('H10', 'N° de Hijos', header_format)
            sheet.write('I10', 'Profesión', header_format)
            sheet.write('J10', 'Cargo Desempeñado', header_format)
            sheet.write('K10', 'Fecha de Entrada', header_format)
            sheet.write('L10', 'Fecha de Salida', header_format)
            sheet.write('M10', 'Motivo de Salida', header_format)
            sheet.write('N10', 'Observaciones', header_format)
            sheet.write('O10', 'Fecha de Nac.', header_format)
            sheet.write('P10', 'Situac. Escolar', header_format)
            sheet.write('Q10', 'Cert. Capac. Exp. En Fecha', header_format)
            sheet.write('R10', 'Horario de Trabajo', header_format)


            empleados_agregados = set()  # Inicializa un conjunto vacío para mantener un registro de los IDs de empleados agregados.

            payslip_records = self.env['hr.payslip'].search(
                [('date_from', '>=', wizard.start_date), ('date_to', '<=', wizard.end_date)])
            empleados_data = {}
            row_num = 10  # Esta es la fila en la que empezarás a escribir los datos. Ajusta según tus necesidades.

            for payslip in payslip_records:
                employee_id = payslip.employee_id.identification_id  # Obtén el ID del empleado de la nómina.
                if employee_id not in empleados_agregados:
                    empleados_agregados.add(employee_id)
                    col_num = 0  # Comenzamos en la primera columna

                    ######################## RUC DE LA COMPAÑIA ###################################
                    registro_compania = payslip.company_id.company_registry if payslip.company_id.company_registry else ''
                    sheet.write(row_num, col_num, registro_compania, contenido)
                    col_num += 1

                    # Divide el nombre completo en nombre y apellido si es posible
                    nombre_completo = payslip.employee_id.name
                    if ',' in nombre_completo:
                        apellido, nombre = nombre_completo.split(',', 1)
                    else:
                        apellido = ''  # O puedes decidir qué hacer en este caso, quizás usar un valor predeterminado
                        nombre = nombre_completo  # Si no hay coma, asumimos que todo es el nombre

                    # Escribe el apellido (si lo hay)
                    sheet.write(row_num, col_num, apellido.strip(), contenido)
                    col_num += 1

                    # Escribe el nombre
                    sheet.write(row_num, col_num, nombre.strip(), contenido)
                    col_num += 1
                    ################## DOMICILIO ################################
                    domicilio = payslip.employee_id.address_home_id.street if payslip.employee_id.address_home_id.street else ''
                    sheet.write(row_num, col_num, domicilio, contenido)
                    col_num += 1
                    ###################### NACIONALIDAD #############################
                    sheet.write(row_num, col_num, payslip.employee_id.country_of_birth.gentilicio, contenido)
                    col_num += 1
                    ############# NUMERO DE IDENTIFICACION  ########################################3
                    sheet.write(row_num, col_num, payslip.employee_id.identification_id, contenido)
                    col_num += 1
                    ######################## EDAD #################################################
                    edad_emple = payslip.employee_id.employee_age if payslip.employee_id.employee_age else ''
                    sheet.write(row_num, col_num, edad_emple, contenido)
                    col_num += 1
                    ###################### numero de hijos ######################################
                    # Calcular el número de hijos directamente y escribir el valor en la hoja
                    contador_hijos = self.calcular_numero_hijos(payslip.employee_id)
                    sheet.write(row_num, col_num, contador_hijos, contenido)
                    col_num += 1
                    ####################### pofesion ############################################33
                    nivel_certificado = payslip.employee_id.certificate
                    certificado_texto = {
                        'graduate': 'Licenciado',
                        'bachelor': 'Graduado',
                        'master': 'Maestro',
                        'doctor': 'Doctor',
                        'other': 'Otro'
                    }
                    texto_a_escribir = certificado_texto.get(nivel_certificado, 'No especificado')
                    sheet.write(row_num, col_num, texto_a_escribir, contenido)
                    col_num += 1
                    ################################## Cargo desempeñado##########################################
                    sheet.write(row_num, col_num, payslip.employee_id.job_title, contenido)
                    col_num += 1

                    ############################## Fecha de entrada ###########################################
                    fecha_entrada = payslip.employee_id.contract_id.date_start.strftime('%d/%m/%Y')
                    sheet.write(row_num, col_num, fecha_entrada, contenido)
                    col_num += 1
                    ########################### Fecha de salida ##############################################
                    # Verificar si el empleado está activo
                    es_activo = payslip.employee_id.active
                    fecha_de_salida = None
                    # Establecer la fecha de salida dependiendo de si el empleado está activo o no
                    if not es_activo:
                        # Si el empleado no está activo, obtener la fecha de salida
                        fecha_de_salida = payslip.employee_id.departure_date
                        if fecha_de_salida:
                            fecha_de_salida = fecha_de_salida.strftime('%d/%m/%Y')  # Formatear fecha si existe
                    else:
                        fecha_de_salida = 0
                    sheet.write(row_num, col_num, fecha_de_salida, contenido)
                    col_num += 1
                    if not es_activo:
                        # Si el empleado no está activo, obtener motivo de salida
                        motivo_de_salida = payslip.employee_id.departure_reason_id.name
                    else:
                        motivo_de_salida = 0
                    sheet.write(row_num, col_num, motivo_de_salida, contenido)
                    col_num += 1

                    ############################         Observacaiones   ########################################
                    if not es_activo:
                        # Si el empleado no está activo, obtener la descripcion de salida
                        descripcion_salida = payslip.employee_id.departure_description

                    else:
                        descripcion_salida = 0
                    sheet.write(row_num, col_num, descripcion_salida, contenido)
                    col_num += 1

                    ###########################     Cumpleaños  ###################################################
                    # Comprobar si la fecha de nacimiento está definida
                    if payslip.employee_id.birthday:
                        fecha_nacimiento = payslip.employee_id.birthday.strftime('%d/%m/%Y')  # Formato día/mes/año
                    else:
                        fecha_nacimiento = 'No especificado'  # O cualquier valor predeterminado que elijas

                    sheet.write(row_num, col_num, fecha_nacimiento, contenido)
                    col_num += 1

                    ########################## SItuacion escolar ##################################################
                    sheet.write(row_num, col_num, '', contenido)
                    col_num += 1

                    #########################     Cert. Capac. Exp. En Fecha ######################################
                    sheet.write(row_num, col_num, '', contenido)
                    col_num += 1


                    ########################## HOrario de Trabajo #######################################
                    sheet.write(row_num, col_num, payslip.employee_id.resource_calendar_id.name, contenido)
                    col_num += 1
                row_num+=1

        else:
            _logger.debug('Este es un mensaje de aviso que el usuario elige imprimir el reporte en formato de importacion')
            sheet.write(0, 0, "N° Patronal", cabecera_no_importacion)
            sheet.write(0, 1, "Documento", cabecera_no_importacion)
            sheet.write(0, 1, "Nombre", cabecera_no_importacion)
            sheet.write(0, 2, "Apellido", cabecera_no_importacion)
            sheet.write(0, 3, "Sexo", cabecera_no_importacion)
            sheet.write(0, 4, "Estadocivil", cabecera_no_importacion)
            sheet.write(0, 5, "Fechanac", cabecera_no_importacion)
            sheet.write(0, 6, "Nacionalidad", cabecera_no_importacion)
            sheet.write(0, 7, "Domicilio", cabecera_no_importacion)
            sheet.write(0, 8, "Fechanacmenor", cabecera_no_importacion)
            sheet.write(0, 9, "hijosmenores", cabecera_no_importacion)
            sheet.write(0, 10, "Cargo", cabecera_no_importacion)
            sheet.write(0, 11, "Profesion", cabecera_no_importacion)
            sheet.write(0, 12, "Fechaentrada", cabecera_no_importacion)
            sheet.write(0, 13, "Horariotrabajo", cabecera_no_importacion)
            sheet.write(0, 14, "Menorescapa", cabecera_no_importacion)
            sheet.write(0, 15, "Menoresescolar", cabecera_no_importacion)
            sheet.write(0, 16, "Fechasalida", cabecera_no_importacion)
            sheet.write(0, 17, "Motivosalida", cabecera_no_importacion)


            empleados_agregados = set()  # Inicializa un conjunto vacío para mantener un registro de los IDs de empleados agregados.

            payslip_records = self.env['hr.payslip'].search(
                [('date_from', '>=', wizard.start_date), ('date_to', '<=', wizard.end_date)])
            empleados_data = {}
            row_num = 1  # Esta es la fila en la que empezarás a escribir los datos. Ajusta según tus necesidades.

            for payslip in payslip_records:
                employee_id = payslip.employee_id.identification_id  # Obtén el ID del empleado de la nómina.
                if employee_id not in empleados_agregados:
                    empleados_agregados.add(employee_id)
                    col_num = 0  # Comenzamos en la primera columna
                    payslip.company_id.company_registry
                    sheet.write(row_num, col_num, payslip.company_id.company_registry, contenido)
                    col_num += 1

                    # Dividir el nombre completo en dos partes usando la coma como separador

                    nombre_completo = payslip.employee_id.name
                    if ',' in nombre_completo:
                        apellido, nombre = nombre_completo.split(',', 1)
                    else:
                        apellido = ''  # O puedes decidir qué hacer en este caso, quizás usar un valor predeterminado
                        nombre = nombre_completo  # Si no hay coma, asumimos que todo es el nombre
                    # Escribir el apellido (o una cadena vacía si no hay apellido) en la hoja de cálculo
                    sheet.write(row_num, col_num, apellido.strip(), contenido)

                    # Moverse a la siguiente columna para el nombre
                    col_num += 1

                    # Escribir el nombre en la hoja de cálculo
                    sheet.write(row_num, col_num, nombre.strip(), contenido)

                    col_num += 1
                    genero = 'M' if payslip.employee_id.gender == 'male' else 'F'

                    sheet.write(row_num, col_num,  genero, contenido)
                    col_num += 1

                    # Obtener el estado civil del empleado y asignar la etiqueta correspondiente
                    estado_civil = payslip.employee_id.marital
                    if estado_civil == 'single':
                        estado_civil_label = 'Soltero(a)'
                    elif estado_civil == 'married':
                        estado_civil_label = 'Casado(a)'
                    elif estado_civil == 'cohabitant':
                        estado_civil_label = 'Cohabitante legal'
                    elif estado_civil == 'widower':
                        estado_civil_label = 'Viudo(a)'
                    elif estado_civil == 'divorced':
                        estado_civil_label = 'Divorciado(a)'
                    else:
                        estado_civil_label = 'Indefinido'  # En caso de que haya otro valor o esté vacío
                    sheet.write(row_num, col_num, estado_civil_label, contenido)
                    col_num += 1

                    # Comprobar si la fecha de nacimiento está definida
                    if payslip.employee_id.birthday:
                        fecha_nacimiento = payslip.employee_id.birthday.strftime('%d/%m/%Y')  # Formato día/mes/año
                    else:
                        fecha_nacimiento = 'No especificado'  # O cualquier valor predeterminado que elijas

                    # Y luego continúas con el resto de tu código...
                    sheet.write(row_num, col_num, fecha_nacimiento, contenido)
                    col_num += 1

                    sheet.write(row_num, col_num, payslip.employee_id.country_of_birth.gentilicio, contenido)
                    col_num += 1

                    sheet.write(row_num, col_num, payslip.employee_id.address_home_id.street, contenido)
                    col_num += 1

                    sheet.write(row_num, col_num, '', contenido)
                    col_num += 1
                    # Calcular el número de hijos directamente y escribir el valor en la hoja
                    contador_hijos = self.calcular_numero_hijos(payslip.employee_id)

                    sheet.write(row_num, col_num, contador_hijos, contenido)
                    col_num += 1

                    sheet.write(row_num, col_num, payslip.employee_id.job_title, contenido)
                    col_num += 1

                    nivel_certificado = payslip.employee_id.certificate

                    # Mapear los valores de 'certificate' a la cadena que deseas mostrar
                    certificado_texto = {
                        'graduate': 'Licenciado',
                        'bachelor': 'Graduado',
                        'master': 'Maestro',
                        'doctor': 'Doctor',
                        'other': 'Otro'
                    }

                    texto_a_escribir = certificado_texto.get(nivel_certificado, 'No especificado')

                    sheet.write(row_num, col_num, texto_a_escribir, contenido)
                    col_num += 1

                    fecha_entrada = payslip.employee_id.contract_id.date_start.strftime('%d/%m/%Y')
                    sheet.write(row_num, col_num, fecha_entrada, contenido)
                    col_num += 1


                    sheet.write(row_num, col_num,payslip.employee_id.resource_calendar_id.name , contenido)
                    col_num += 1


                    sheet.write(row_num, col_num,0 , contenido)
                    col_num += 1

                    sheet.write(row_num, col_num,0 , contenido)
                    col_num += 1

                    # Verificar si el empleado está activo
                    es_activo = payslip.employee_id.active

                    fecha_de_salida = None

                    # Establecer la fecha de salida dependiendo de si el empleado está activo o no
                    if not es_activo:
                        # Si el empleado no está activo, obtener la fecha de salida
                        fecha_de_salida = payslip.employee_id.departure_date
                        if fecha_de_salida:
                            fecha_de_salida = fecha_de_salida.strftime('%d/%m/%Y')  # Formatear fecha si existe
                    else:
                        fecha_de_salida =  0
                    sheet.write(row_num, col_num,fecha_de_salida , contenido)
                    col_num += 1
                    if not es_activo:
                        # Si el empleado no está activo, obtener la fecha de salida
                        motivo_de_salida = payslip.employee_id.departure_reason_id.name
                    else:
                        motivo_de_salida= 0

                    sheet.write(row_num, col_num, motivo_de_salida, contenido)

                    row_num+=1


    def calcular_numero_hijos(self, empleado):
        contador_hijos = 0
        for gf in empleado.grupo_familiar_id:
            if (gf.edad < 17 and gf.relacion_parentesco == 'hijo' ) or (
                    gf.discapacitado == 'si' and gf.relacion_parentesco == 'hijo' ):
                contador_hijos += 1
        return contador_hijos

