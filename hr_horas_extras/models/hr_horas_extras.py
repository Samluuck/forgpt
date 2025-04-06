from pytz import timezone, utc
from datetime import datetime, timedelta, date, time
import logging
from datetime import datetime, timedelta, date
from pytz import timezone, UTC
import pytz
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    horas_diurnas = fields.Float(string="Horas extras diurnas", compute='_compute_hours_diurno', store=True)
    horas_nocturnas = fields.Float(string="Horas extras nocturnas", compute='_compute_hours_nocturno', store=True)
    horas_domifer = fields.Float(string="Horas extras domingo/feriado", compute='_compute_hours_domifer', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_hours_diurno(self):
        print("*************7862589+32589+3**************")
        for attendance in self:
            if attendance.check_in and attendance.check_out and attendance.employee_id.cobra_horas_extras:
                # Obtener el horario diurno desde la configuración
                horario_diurno_config = self.env['ir.config_parameter'].sudo().get_param(
                    'hr_horas_extras.horario_diurno')
                # Verificar si horario_diurno_config tiene el formato esperado (ejemplo: "18:30")
                if ':' in horario_diurno_config:
                    horas, minutos = horario_diurno_config.split(':')
                    # Convertir horas y minutos a decimal
                    hora_extra_diurno = float(horas) + float(minutos) / 60
                else:
                    # Valor por defecto si horario_diurno_config no tiene el formato esperado
                    hora_extra_diurno = 18.0  # Valor por defecto es 18:00
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!111",hora_extra_diurno)
                # Convertir el valor decimal a horas y minutos
                horas = int(hora_extra_diurno)
                minutos = int((hora_extra_diurno - horas) * 60)
                # Crear un objeto 'time' con las horas y minutos
                hora_extra_diurno_time = time(horas, minutos, 0)
                # Convertir las marcas de tiempo a la zona horaria de Asunción
                timezone_asuncion = timezone('America/Asuncion')
                check_in_local = utc.localize(attendance.check_in).astimezone(timezone_asuncion)
                check_out_local = utc.localize(attendance.check_out).astimezone(timezone_asuncion)

                # Imprimir para depuración
                print(f"Check-in local: {check_in_local}")
                print(f"Check-out local: {check_out_local}")
                print(f"Hora inicio horas extras: {hora_extra_diurno_time}")

                if check_out_local.time() > hora_extra_diurno_time:
                    # Calcular la diferencia de tiempo
                    check_out_local_td = timedelta(hours=check_out_local.hour, minutes=check_out_local.minute,
                                                   seconds=check_out_local.second)
                    hora_extra_diurno_td = timedelta(hours=hora_extra_diurno_time.hour,
                                                     minutes=hora_extra_diurno_time.minute,
                                                     seconds=hora_extra_diurno_time.second)
                    diferencia_tiempo_td = check_out_local_td - hora_extra_diurno_td

                    # Imprimir para depuración
                    print(f"Diferencia tiempo: {diferencia_tiempo_td}")

                    diferencia_tiempo_horas = (diferencia_tiempo_td.total_seconds() / 3600)
                    print("**********************************",diferencia_tiempo_horas)
                    attendance.horas_diurnas = diferencia_tiempo_horas
                else:
                    attendance.horas_diurnas = 0.0
            else:
                attendance.horas_diurnas = 0.0

    @api.depends('check_in', 'check_out')
    def _compute_hours_nocturno(self):
        _logger.warning('*********************  _compute_hours_nocturno  *******************')

        for attendance in self:
            if attendance.check_in and attendance.check_out and attendance.employee_id.cobra_horas_extras:
                # Obtener el valor de horas_nocturnas desde la configuración de asistencias
                horas_nocturnas_config = self.env['ir.config_parameter'].sudo().get_param(
                    'hr_horas_extras.horas_nocturnas', default=False)

                # Verificar si horas_nocturnas_config tiene un valor configurado
                if horas_nocturnas_config and ':' in horas_nocturnas_config:
                    horas, minutos = horas_nocturnas_config.split(':')
                    # Convertir horas y minutos a decimal
                    hora_extra_nocturno = float(horas) + float(minutos) / 60
                else:
                    # Si no hay un valor en horas_nocturnas, usamos el valor por defecto 22:00
                    hora_extra_nocturno = 22.0  # Valor por defecto es 22:00

                _logger.warning(f"Valor de horas nocturnas: {hora_extra_nocturno}")

                # Convertir el valor decimal a horas y minutos
                horas = int(hora_extra_nocturno)
                minutos = int((hora_extra_nocturno - horas) * 60)

                # Crear un objeto 'time' con las horas y minutos
                hora_extra_nocturno_time = time(horas, minutos, 0)

                # Convertir las marcas de tiempo a la zona horaria de Asunción
                timezone_asuncion = timezone('America/Asuncion')
                check_in_local = utc.localize(attendance.check_in).astimezone(timezone_asuncion)
                check_out_local = utc.localize(attendance.check_out).astimezone(timezone_asuncion)

                # Imprimir para depuración
                _logger.warning(f"Check-in local: {check_in_local}")
                _logger.warning(f"Check-out local: {check_out_local}")
                _logger.warning(f"Hora inicio horas extras nocturnas: {hora_extra_nocturno_time}")

                if check_out_local.time() > hora_extra_nocturno_time:
                    # Calcular la diferencia de tiempo
                    check_out_local_td = timedelta(hours=check_out_local.hour, minutes=check_out_local.minute,
                                                   seconds=check_out_local.second)
                    hora_extra_nocturno_td = timedelta(hours=hora_extra_nocturno_time.hour,
                                                       minutes=hora_extra_nocturno_time.minute,
                                                       seconds=hora_extra_nocturno_time.second)
                    diferencia_tiempo_td = check_out_local_td - hora_extra_nocturno_td

                    # Imprimir para depuración
                    _logger.warning(f"Diferencia tiempo: {diferencia_tiempo_td}")

                    diferencia_tiempo_horas = (diferencia_tiempo_td.total_seconds() / 3600)
                    _logger.warning(f"Horas nocturnas calculadas: {diferencia_tiempo_horas}")
                    attendance.horas_nocturnas = diferencia_tiempo_horas
                else:
                    attendance.horas_nocturnas = 0.0
            else:
                attendance.horas_nocturnas = 0.0

    @api.depends('check_in', 'check_out')
    def _compute_hours_domifer(self):
        """
        Cálculo de horas extras para domingo o feriado.
        - Feriado: existe registro en resource.calendar.leaves (sin resource_id) que contenga la fecha.
        """
        print("################################      INGRESA EN _compute_hours_domifer ########################################## ")
        resource_calendar_leaves = self.env['resource.calendar.leaves']

        # Zona horaria de Asunción (para analizar correctamente el día real)
        timezone_asuncion = timezone('America/Asuncion')

        for attendance in self:
            attendance.horas_domifer = 0.0  # Valor por defecto

            if attendance.check_in and attendance.check_out and attendance.employee_id.cobra_horas_extras:
                # Convertir check_in y check_out a zona horaria local
                check_in_local = utc.localize(attendance.check_in).astimezone(timezone_asuncion)
                check_out_local = utc.localize(attendance.check_out).astimezone(timezone_asuncion)
                fecha_marcacion = check_in_local.date()
                _logger.warning(f"Fecha marcacion local: {fecha_marcacion}")

                # Verificar si es domingo (weekday: 0=lunes,...,6=domingo)
                es_domingo = (fecha_marcacion.weekday() == 6)

                # Verificar si es feriado
                feriados = resource_calendar_leaves.search([
                    ('date_from', '<=', fecha_marcacion),
                    ('date_to', '>=', fecha_marcacion),
                    ('resource_id', '=', False),  # Feriados sin recurso específico
                ])
                es_feriado = bool(feriados)

                # Si es domingo O es feriado, calculamos la diferencia de horas
                if es_domingo or es_feriado:
                    _logger.warning("******** ES DOMINGO O FERIADO ********")
                    horas_trabajadas = (check_out_local - check_in_local).total_seconds() / 3600
                    attendance.horas_domifer = horas_trabajadas

                    _logger.warning(
                        f"Domingo={es_domingo}, Feriado={es_feriado}, horas_domifer={attendance.horas_domifer}")
                else:
                    _logger.warning("******** NO ES DOMINGO NI FERIADO; horas_domifer=0 ********")
                    attendance.horas_domifer = 0.0
            else:
                _logger.warning("******** Falta check_in/check_out o cobra_horas_extras=False ********")
                attendance.horas_domifer = 0.0