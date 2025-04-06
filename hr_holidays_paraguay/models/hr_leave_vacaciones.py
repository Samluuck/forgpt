import logging
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions
import datetime

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def _verificar_vacaciones(self):
        _logger.warning(
            " ****************************** Ingresa en _verificar_vacaciones *****************************")
        empleados = self.env['hr.employee'].search([('calcula_vacaciones', '=', True)])
        _logger.warning("Empleados  %s", empleados)
        fecha_actual = fields.Date.today()
        anio_actual = datetime.datetime.now().year
        tipo_vacaciones = self.env['hr.leave.type'].search([('es_vacacion', '=', True)], limit=1)
        _logger.warning("TIPO VACACIONES funcion  %s", tipo_vacaciones)
        contrato_model = self.env['hr.contract']

        adelanto_vacaciones = self.env['hr.leave.type'].search([('adelanto_vacaciones', '=', True)], limit=1)
        _logger.warning('ADELANTO VACACIONES  %s', adelanto_vacaciones)

        for emp in empleados:
            contrato = contrato_model.search([('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
            if not contrato:
                _logger.warning("El empleado %s no tiene contrato activo.", emp.name)
                continue
            #     ####
            _logger.warning("********************  NOMBRE DE EL EMPLEADO ************* %s", emp.name)
            dias_utilizados_periodo = 0
            _logger.warning("TIPO VACACIONES %s", tipo_vacaciones)
            _logger.warning("TIPO ID  %s", tipo_vacaciones.id)

            _logger.warning('fecha_actual %s (%s)', fecha_actual, str(type(fecha_actual)))
            # _logger.warning('TIPOS DE AUSENCIAS DEL EMPLEADO %s', )
            tiene_adelanto_vacaciones = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', adelanto_vacaciones.id),
                ('state', '=', 'validate'),
            ])

            cantidad_vacaciones_emp_actual = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', tipo_vacaciones.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', fecha_actual),
            ])
            _logger.warning("hr leave emp id  %s", emp.id)
            _logger.warning("hr leave tipo vacaciones id  %s", tipo_vacaciones.id)
            _logger.warning("hr fecha actual  %s", fecha_actual)
            _logger.warning("CANTIDAD VACACIONES %s", cantidad_vacaciones_emp_actual)

            _logger.warning('TIENE ADELANTO??????   %s', tiene_adelanto_vacaciones)

            # if cantidad_vacaciones_emp_actual:
            #     dias_utilizados_periodo = sum(va.number_of_days for va in cantidad_vacaciones_emp_actual)
            #     _logger.warning('DIAS UTILIZADOS PERIODO  %s', dias_utilizados_periodo)

            if tiene_adelanto_vacaciones:
                dias_utilizados_periodo = sum(va.number_of_days for va in tiene_adelanto_vacaciones)
                _logger.warning('DIAS UTILIZADOS PERIODO  %s', dias_utilizados_periodo)

            if tiene_adelanto_vacaciones:
                _logger.warning('HA ADELANTADO ALGUNOS DIAS DE ESTE PERIODO %s', tiene_adelanto_vacaciones)

            _logger.warning("************************************* dias utilizados periodo %s", dias_utilizados_periodo)
            dias_vacaciones_asignadas = self.calcular_dias_vacaciones(emp, contrato)
            # seteo a cero temporal
            saldo_dias = 0 if dias_vacaciones_asignadas == 0 else dias_vacaciones_asignadas - dias_utilizados_periodo
            _logger.warning(" **************************** El saldo de días es: %s", saldo_dias)
            # Esto es temporal para evitar el raise que levantaba al tener saldo menor a cero y evitaba que se siga calculando para el resto de registros
            # se debe volver a manejar este error al ajustar el resto de testcases
            if saldo_dias < 0:
                _logger.warning('SALDO DIAS MENOR A CERO, SETEANDO A CERO  %s', emp.name)
                saldo_dias = 0
                # raise exceptions.ValidationError('El saldo de días de vacaciones no puede ser negativo.')

            if saldo_dias > 0:  # Si cumple con la antigüedad requerida
                # asignacion_existente = self.env['hr.leave.allocation'].search([
                #     ('employee_id', '=', emp.id),
                #     ('state', '=', 'validate'),
                #     ('holiday_status_id', '=', tipo_vacaciones.id),
                # ], limit=1)
                # Verificar si hay una asignación existente dentro del periodo
                # Es decir, hoy hacia atras 11 meses para evitar duplicados
                asignacion_existente = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('state', '=', 'validate'),
                    ('holiday_status_id', '=', tipo_vacaciones.id),
                    ('date_from', '>=', (fields.Date.today() - relativedelta(months=11)).strftime('%Y-%m-%d')),  # Desde hoy hace 11 meses
                ], limit=1)

                if asignacion_existente:
                    continue
                #     _logger.warning('ASIGNACION EXISTENTE  %s', asignacion_existente)
                #     _logger.warning('ASIGNACION DIAS despues del write %s', asignacion_existente.number_of_days)
                #else:
                #    vals = {
                #        'name': 'Asignación de vacaciones para ' + emp.name,
                #        'holiday_status_id': tipo_vacaciones.id,
                #        'holiday_type': 'employee',
                #        'employee_id': emp.id,
                #        'number_of_days': saldo_dias,
                #        'date_from': fecha_actual,
                #    }
                #     _logger.warning('SIN ASIGNACION  %s', vals)
                #
                #     allocation = self.env['hr.leave.allocation'].create(vals)
                #     allocation.action_confirm()  # Confirma la asignación de vacacions
                #     allocation.action_validate()  # Aprueba la asignación de vacaciones
                #_logger.warning('ASIGNACION EXISTENTE  %s', asignacion_existente)
                #_logger.warning('ASIGNACION DIAS antes %s', asignacion_existente.number_of_days)

                vals = {
                    'name': 'Asignación de vacaciones para ' + emp.name,
                    'holiday_status_id': tipo_vacaciones.id,
                    'holiday_type': 'employee',
                    'employee_id': emp.id,
                    'number_of_days': saldo_dias,
                    'date_from': fecha_actual,
                }
                _logger.warning('SIN ASIGNACION  %s', vals)

                allocation = self.env['hr.leave.allocation'].create(vals)
                allocation.action_confirm()  # Confirma la asignación de vacacions
                allocation.action_validate()  # Aprueba la asignación de vacaciones

            else:
                _logger.warning("********** El empleado %s no cumple con la antigüedad requerida para vacaciones.",
                                emp.name)

    def calcular_dias_vacaciones(self, empleado, contrato):
        _logger.warning("Ingresa en calcular_dias_vacaciones")
        # Se muda la verificacion del contrato dentro del ciclo for para evitar la interrupcion del resto si se encuentra un False entre los registros
        # contrato = contrato_model.search([('employee_id', '=', empleado.id), ('state', '=', 'open')])
        # if contrato:
        fecha_incorporacion = contrato.date_start
        fecha_hoy = fields.Date.today() + relativedelta(months=1) # Sumamo 1 mes para que asigne un mes antes de cumplir su antiguedad
        cantidad_dias = (fecha_hoy - fecha_incorporacion).days
        _logger.warning("La cantidad de días en la empresa dentro de un mes: %s", cantidad_dias)
        _logger.warning("CANTIDAD EN MESES: %s", cantidad_dias / 30)
        dias_vacaciones = self.calcular_dias_disponibles(cantidad_dias)
        return dias_vacaciones
        # else:
        #     # raise exceptions.ValidationError('No existe un contrato activo para el empleado %s' % empleado.name)
        #     pass # Posible conflicto ya que no interrumpira el ciclo en el for, manejar el caso desde dentro del for!

    def calcular_dias_disponibles(self, cantidad):
        anios = cantidad // 365  # Anhos desde inicio
        # meses = (cantidad % 365) // 30  # Meses transcurridos de este periodo

        # Dias correspondientes segun antiguedad
        if anios < 1:
            dias_vacaciones = 0
        elif 1 <= anios < 6:
            dias_vacaciones = 12
        elif 6 <= anios < 11:
            dias_vacaciones = 18
        else:
            dias_vacaciones = 30
        """
        Ajustar dias correspondientes para vacaciones proporcionales
        VERIFICAR restriccion para vacaciones antes de 6 meses causa conflictos para que sea retroactivo
        if meses menos a 6 desmarcar calcular vacaciones asi se puede eliminar restriccion para cuando antiguedad es menor a 6 meses
        Pero para este caso se debe manejar cumpleanhos que depende de esa casilla y si es menor a 6 meses no le activaria el calculo
        otra posible solucion es quitar el calculo de vacaciones proporcionales de abajo para dejar que se haga manualmente con la ausencia Adelanto Vacaciones
        asi modificamos if meses < 6 and anios = 0 para distinguir si es el primer periodo y menor a 6 meses que aun no accede a vacaciones
        """

        # if meses < 6
        # if meses < 6 and anios > 1:
        #     dias_vacaciones = 0
        # if meses >= 6 and meses < 12:  # Si ya han transcurrido mas de 6 meses de este periodo ya puede acceder a vacaciones proporcionales
        #     dias_vacaciones = dias_vacaciones // 2
        return dias_vacaciones

    def verificar_y_asignar_cumpleanios(self):
        _logger.warning("Ingresa en verificar_y_asignar_cumpleanios")
        empleados = self.env['hr.employee'].search([('calcula_vacaciones', '=', True)])
        fecha_actual = fields.Date.today()
        tipo_cumpleanios = self.env['hr.leave.type'].search([('es_cumpleaños', '=', True)], limit=1)
        _logger.warning('TIPO DE AUSENCIA CUMPLEANHOS???????   %s', tipo_cumpleanios)

        for emp in empleados:
            _logger.warning("Procesando empleado: %s", emp.name)

            # Verificar si el empleado tiene una fecha de cumpleaños registrada
            if emp.birthday:
                fecha_cumpleanios = fields.Date.from_string(emp.birthday).replace(year=fecha_actual.year)
                _logger.warning("LA FECHA DE CUMPLE DE EL EMPLEADO ES: %s", fecha_cumpleanios)

                # Verificar si el cumpleaños es dentro de 15 días
                if 0 <= (fecha_cumpleanios - fecha_actual).days <= 15:
                    _logger.warning('EL CUMPLEAÑOS DEL EMPLEADO %s ES EN 15 DÍAS O MENOS', emp.name)
                    # Verificar si ya existe una asignación de día libre por cumpleaños en el periodo
                    asignacion_existente = self.env['hr.leave.allocation'].search([
                        ('employee_id', '=', emp.id),
                        ('holiday_status_id', '=', tipo_cumpleanios.id),
                        ('state', '=', 'validate'),
                        ('date_from', '>=', (fields.Date.today() - relativedelta(months=11)).strftime('%Y-%m-%d')),
                    ], limit=1)

                    _logger.warning("hr leave emp id  %s", emp.id)
                    _logger.warning("hr fecha actual  %s", fecha_actual)
                    _logger.warning("Asignacion existente  %s", asignacion_existente)
                    _logger.warning('TIPO CUMPLEANIOS  %s', tipo_cumpleanios)
                    _logger.warning('TIPO CUMPLEANIOS ID  %s', tipo_cumpleanios.id)

                    if not asignacion_existente:
                        _logger.info("NO EXISTE ASIGNACION")
                        vals = {
                            'name': 'Asignación de día libre por cumpleaños para ' + emp.name,
                            'holiday_status_id': tipo_cumpleanios.id,
                            'holiday_type': 'employee',
                            'employee_id': emp.id,
                            'number_of_days': 1,  # Suponiendo que se otorga 1 día por cumpleaños
                            'date_from': fecha_actual,  # Asignar desde la fecha actual
                            'date_to': fecha_cumpleanios + relativedelta(days=15),  # Termina 15 días después del cumpleaños
                        }
                        _logger.warning("VALSSSSS   %s", vals)
                        _logger.warning('TIPPOAOP CUMPLE  %s', tipo_cumpleanios)
                        _logger.warning("tipo CUMPLEEE ID", tipo_cumpleanios.id)
                        allocation = self.env['hr.leave.allocation'].create(vals)
                        allocation.action_confirm()
                        allocation.action_validate()
                    else:
                        _logger.warning(
                            "Ya existe una asignación de día libre por cumpleaños para el empleado %s en este mes.",
                            emp.name)

                else:
                    _logger.warning("No es el mes de cumpleaños para el empleado %s", emp.name)

    @api.model
    def cron_actions(self):
        self._verificar_vacaciones()
        self.verificar_y_asignar_cumpleanios()
