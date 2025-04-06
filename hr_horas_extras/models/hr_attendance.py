from datetime import datetime, timedelta
import pytz
from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    early_check_in = fields.Integer(string="Llegada anticipada (Minutos)", compute="get_early_minutes")
    late_check_in = fields.Integer(string="Llegada tardía (Minutos)", compute="get_late_minutes")

    def get_late_minutes(self):
        print("Ingresa a get_late_minutes ")
        for rec in self:
            minutes_tolerance = int(self.env['ir.config_parameter'].sudo().get_param('hr_horas_extras.tolerancia_llegada_tardia', 0))
            print("___________________ MINUTOS tolerancia:   ", minutes_tolerance)
            rec.late_check_in = 0  # Cambiado a 0 en lugar de 0.0

            # Verifica si rec.check_in es un datetime antes de proceder
            if isinstance(rec.check_in, datetime):
                week_day = rec.check_in.weekday()
                work_schedule = rec.sudo().employee_id.contract_id.resource_calendar_id

                # Obtener la hora de inicio programada para el día correspondiente
                scheduled_hour_from = None
                for schedule in work_schedule.sudo().attendance_ids:
                    if schedule.dayofweek == str(week_day):
                        scheduled_hour_from = schedule.hour_from
                        break

                if scheduled_hour_from is not None:
                    # Calcular la hora programada en formato datetime
                    scheduled_time = timedelta(hours=scheduled_hour_from)

                    # Obtener la hora de check-in y convertir a la misma zona horaria
                    user_tz = self.env.user.tz or 'UTC'  # Proporcionar un valor por defecto
                    check_in_local = rec.check_in.astimezone(pytz.timezone(user_tz))  # Convertir a la zona horaria del usuario
                    check_in_time = timedelta(hours=check_in_local.hour, minutes=check_in_local.minute)

                    # Calcular la diferencia en minutos
                    diferencia_min = (check_in_time - scheduled_time).total_seconds() / 60

                    # Verifica si llegó tarde
                    if diferencia_min > minutes_tolerance:
                        rec.late_check_in = diferencia_min

                    print("Cantidad de minutos tarde ", rec.late_check_in)
                else:
                    print("No se encontró un horario programado para el día correspondiente.")
            else:
                print("rec.check_in no es un datetime.")

    def late_check_in_records(self):
        existing_records = self.env['late.check_in'].sudo().search([]).attendance_id.ids
        minutes_after = int(self.env['ir.config_parameter'].sudo().get_param('late_check_in_after'))
        max_limit = int(self.env['ir.config_parameter'].sudo().get_param('maximum_minutes')) or 0
        late_check_in_ids = self.sudo().search([('id', 'not in', existing_records)])
        for rec in late_check_in_ids:
            late_check_in = rec.sudo().late_check_in + 210
            if rec.late_check_in >= minutes_after:
                self.env['late.check_in'].sudo().create({
                    'employee_id': rec.employee_id.id,
                    'late_minutes': late_check_in,
                    'date': rec.check_in.date(),
                    'attendance_id': rec.id,
                })

    def get_early_minutes(self):
        print("Entra en get_early_minutes ")
        for rec in self:
            rec.early_check_in = 0
            # Verificamos que check_in no sea nulo o False
            if rec.check_in and rec.employee_id.cobra_entrada_anticipada:
                minutes_tolerance = int(self.env['ir.config_parameter'].sudo().get_param('hr_horas_extras.tolerancia_llegada_anticipada', 0))
                # Obtenemos el día de la semana solo si check_in es una fecha válida
                week_day = rec.check_in.weekday()
                if rec.employee_id.contract_id:
                    work_schedule = rec.employee_id.contract_id.resource_calendar_id
                    for schedule in work_schedule.attendance_ids:
                        if schedule.dayofweek == str(week_day) and schedule.day_period == 'morning':
                            work_from = schedule.hour_from
                            result = '{0:02.0f}:{1:02.0f}'.format(*divmod(work_from * 60, 60))
                            user_tz = self.env.user.tz or 'UTC'
                            dt = rec.check_in
                            old_tz = pytz.timezone('UTC')
                            new_tz = pytz.timezone(user_tz)
                            dt = old_tz.localize(dt).astimezone(new_tz)
                            str_time = dt.strftime("%H:%M")
                            check_in_date = datetime.strptime(str_time, "%H:%M").time()
                            start_date = datetime.strptime(result, "%H:%M").time()
                            t1 = timedelta(hours=check_in_date.hour, minutes=check_in_date.minute)
                            t2 = timedelta(hours=start_date.hour, minutes=start_date.minute)
                            if t2 > t1:
                                diferencia = t2 - t1
                                if diferencia.total_seconds() / 60 > minutes_tolerance:
                                    rec.early_check_in = diferencia.total_seconds() / 60
            else:
                print(f"No hay registro de check_in o cobra_entrada_anticipada para el empleado {rec.employee_id.name}")
