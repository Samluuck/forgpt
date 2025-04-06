# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import datetime, timedelta
import pytz
import time
from . import const
from .base import ZK

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)


class zkMachineLocation(models.Model):
    _name = 'zk.machine.location'
    name = fields.Char("Location", required=True)


class zkMachine(models.Model):
    _name = 'zk.machine'

    name = fields.Char("IP de la máquina")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'State', default='draft')
    location_id = fields.Many2one('zk.machine.location', string="Ubicación")
    port = fields.Integer("Numero del Puerto")
    employee_ids = fields.Many2many("hr.employee", 'zk_machine_employee_rel', 'employee_id', 'machine_id',
                                    string='Empleados', readonly=True, copy=False, required=False)
    activo = fields.Boolean(string="El reloj se encuentra activo?")

    def try_connection(self):
        for r in self:
            machine_ip = r.name
            port = r.port
            zk = ZK(machine_ip, port=port, timeout=120, password=0, force_udp=False, ommit_ping=True)
            conn = ''
            try:
                conn = zk.connect()
                users = conn.get_users()
            except Exception as e:
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.disconnect()
                    raise UserError(_('Conexión exitosa: "%s".') %
                                    (users))

    def restart(self):
        for r in self:
            machine_ip = r.name
            port = r.port
            zk = ZK(machine_ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=True)
            conn = ''
            try:
                conn = zk.connect()
                conn.restart()
            except Exception as e:
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                raise UserError('Exitosa')

    def synchronize(self):
        for r in self:
            employee = self.env['hr.employee']
            employee_location_line = self.env['zk.employee.location.line']
            employee_list = []
            machine_ip = r.name
            port = r.port
            zk = ZK(machine_ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=True)
            conn = ''
            try:
                conn = zk.connect()
                conn.disable_device()
                users = conn.get_users()
                for user in users:
                    employee_id = employee.search([('zknumber', '=', user.user_id)])
                    if employee_id:
                        employee_list.append(employee_id)
                        if employee_id not in r.employee_ids:
                            r.employee_ids += employee_id
                            employee_location_line.create({'employee_id': employee_id.id,
                                                           'zk_num': employee_id.zknumber,
                                                           'machine_id': r.id,
                                                           'uid': user.uid,
                                                           'location_id': r.location_id.id})
                for emp in employee_list:
                    employee += emp
                employees_unlink = r.employee_ids - employee
                for emp1 in employees_unlink:
                    employee_location_line_id = employee_location_line.search(
                        [('employee_id', '=', emp1.id), ('machine_id', '=', r.id)])
                    employee_location_line_id.unlink()
                r.employee_ids = employee
            except Exception as e:
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.disconnect()

    def clear_attendance(self):
        for r in self:
            machine_ip = r.name
            port = r.port
            zk = ZK(machine_ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=True)
            conn = ''
            try:
                conn = zk.connect()
                conn.disable_device()
                conn.clear_attendance()
            except Exception as e:
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.enable_device()
                    conn.disconnect()

    def download_attendance2(self):
        users = self.env['res.users']
        attendance_obj = self.env["hr.attendance"]
        employee_location_line_obj = self.env["zk.employee.location.line"]
        user = self.env.user
        if not user.partner_id.tz:
            raise exceptions.ValidationError("La zona horaria no está definida en este usuario de% s." % user.name)
        tz = pytz.timezone(user.partner_id.tz) or False
        for machine in self:
            machine_ip = machine.name
            port = machine.port
            zk = ZK(machine_ip, port=port, timeout=50, password=0, force_udp=False, ommit_ping=True)
            conn = ''
            try:
                conn = zk.connect()
                attendances = conn.get_attendance()
            except Exception as e:
                print(e)
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.disconnect()
                    raise UserError(_('Conexión exitosa: "%s".') %
                                    (attendances))

    def download_attendance_0_1(self):
        _logger.warning('********************* ENTRA EN download_attendance_0_1 *******************')

        attendance_obj = self.env["hr.attendance"]
        user = self.env.user

        if not user.partner_id.tz:
            raise UserError("La zona horaria no está definida en este usuario de %s." % user.name)

        tz = pytz.timezone(user.partner_id.tz)
        anio_actual = datetime.now().year

        for machine in self:
            machine_ip = machine.name
            port = machine.port
            zk = ZK(machine_ip, port=port, timeout=10, password=0, force_udp=False, ommit_ping=True)
            conn = None

            try:
                conn = zk.connect()
                conn.disable_device()
                attendances_unfiltered = conn.get_attendance()

                asistencias_por_empleado = {}
                for asistencia in attendances_unfiltered:
                    if asistencia.punch not in [0, 1, 4, 5]:
                        continue

                    if asistencia.timestamp.year != anio_actual:
                        continue

                    user_id = asistencia.user_id
                    if user_id not in asistencias_por_empleado:
                        asistencias_por_empleado[user_id] = []
                    asistencias_por_empleado[user_id].append(asistencia)

                for user_id, attendances in asistencias_por_empleado.items():
                    employee_id = self.env['hr.employee'].search([('zknumber', '=', str(user_id))], limit=1)
                    if not employee_id:
                        continue

                    attendances.sort(key=lambda x: x.timestamp)

                    for attendance in attendances:
                        date_orig = tz.localize(attendance.timestamp).astimezone(pytz.UTC)
                        date = date_orig.astimezone(pytz.UTC)  # Asegurar UTC

                        is_punch_new_system = attendance.punch in [0, 1, 4, 5]
                        is_check_in = attendance.punch in [0, 4]
                        is_check_out = attendance.punch in [1, 5]

                        _logger.warning(
                            f"📌 Procesando asistencia: {employee_id.name} - {date.strftime('%Y-%m-%d %H:%M:%S')} (Punch: {attendance.punch})")

                        # 🔹 Buscar si ya existe esta asistencia como check_in o check_out
                        existing_attendance = attendance_obj.search([
                            ('employee_id', '=', employee_id.id),
                            '|',
                            ('check_in', '=', date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                            ('check_out', '=', date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                        ], limit=1)

                        if existing_attendance:
                            _logger.warning(
                                f"❌ IGNORANDO duplicado: {employee_id.name} - {date.strftime('%Y-%m-%d %H:%M:%S')}")
                            continue

                        last_attendance = None

                        if is_check_out:
                            last_attendance = attendance_obj.search([
                                ('employee_id', '=', employee_id.id),
                                ('check_out', '=', False),
                                ('machine_id', '=', machine.id),
                                ('check_in', '<=', date.strftime('%Y-%m-%d %H:%M:%S'))
                            ], order='check_in desc', limit=1)

                        if last_attendance and last_attendance.check_in and not last_attendance.check_out:
                            check_in_dt = last_attendance.check_in.replace(tzinfo=None)
                            date_naive = date.replace(tzinfo=None)

                            diferencia_horas = (date_naive - check_in_dt).total_seconds() / 3600
                            _logger.warning(
                                f"✅ Diferencia corregida: {diferencia_horas:.2f} horas para {employee_id.name}")

                            if 0 < diferencia_horas <= 15:
                                _logger.warning(
                                    f"✅ UNIFICANDO check_out: {employee_id.name} - {check_in_dt.strftime('%Y-%m-%d %H:%M:%S')} --> {date_naive.strftime('%Y-%m-%d %H:%M:%S')}")
                                last_attendance.write(
                                    {'check_out': date_naive.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                            else:
                                _logger.warning(
                                    f"⚠️ Check_out fuera de rango, creando registro separado para {employee_id.name}")
                                attendance_obj.create({
                                    'employee_id': employee_id.id,
                                    'check_in': False,
                                    'check_out': date_naive.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'machine_id': machine.id,
                                })

                        elif is_check_in:
                            _logger.warning(f"🔹 CREANDO NUEVO check_in para {employee_id.name}")
                            attendance_obj.create({
                                'employee_id': employee_id.id,
                                'check_in': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'machine_id': machine.id,
                            })

            except Exception as e:
                _logger.error("Error al conectar con el dispositivo: %s" % e)
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.enable_device()
                    conn.disconnect()

    def get_employee_schedule(self, employee, check_date):
        """ Obtiene el horario del empleado en un día específico basado en resource.calendar.attendance """
        if not employee.resource_calendar_id:
            _logger.warning(f"⚠️ {employee.name} no tiene un horario de trabajo asignado.")
            return None

        check_day = str(check_date.weekday())  # Odoo usa '0' para lunes, ..., '6' para domingo

        schedule = self.env['resource.calendar.attendance'].search([
            ('calendar_id', '=', employee.resource_calendar_id.id),
            ('dayofweek', '=', check_day),
        ])

        if not schedule:
            _logger.warning(f"⚠️ No se encontró horario para {employee.name} el {check_date.strftime('%A')}.")
            return None

        work_schedules = []
        for entry in schedule:
            work_start = timedelta(hours=entry.hour_from)
            work_end = timedelta(hours=entry.hour_to)
            work_schedules.append((work_start, work_end))

        _logger.warning(f"✅ Horario encontrado para {employee.name} el {check_date.strftime('%A')}: {work_schedules}")
        return work_schedules

    def can_unify_attendance(self, employee, check_datetime, last_check_in):
        """ Determina si un check-in y un check-out pueden unirse según el horario del empleado """
        work_schedules = self.get_employee_schedule(employee, check_datetime)

        if not work_schedules:
            _logger.warning(f"⚠️ No se encontró horario para {employee.name}. Permitiendo unión por defecto.")
            return True  # ✅ Si no hay horario, se permite unir

        check_date = check_datetime.date()
        last_check_date = last_check_in.date()

        for work_start, work_end in work_schedules:
            work_start_time = (datetime.min + work_start).time()
            work_end_time = (datetime.min + work_end).time()
            check_time = check_datetime.time()
            last_check_time = last_check_in.time()

            # 📌 Caso 1: Turno dentro del mismo día (Ej: 07:00 - 17:30)
            if work_start < work_end:
                if check_date == last_check_date:  # ✅ Ambos registros en el mismo día
                    return True

            # 📌 Caso 2: Turno cruza la medianoche (Ej: 22:00 - 03:30)
            else:
                diff_hours = (check_datetime - last_check_in).total_seconds() / 3600
                if diff_hours <= 14:  # ✅ Permitir si la diferencia es menor a 14 horas
                    return True

        _logger.warning(f"⚠️ No se pudo unir asistencia de {employee.name}, fuera del horario permitido.")
        return False

    def download_attendance_255(self):
        _logger.warning('********************* ENTRA EN download_attendance_255 *******************')

        attendance_obj = self.env["hr.attendance"]
        user = self.env.user

        if not user.partner_id.tz:
            raise UserError("La zona horaria no está definida en este usuario de %s." % user.name)

        tz = pytz.timezone(user.partner_id.tz)
        anio_actual = datetime.now().year

        for machine in self:
            machine_ip = machine.name
            port = machine.port
            zk = ZK(machine_ip, port=port, timeout=10, password=0, force_udp=False, ommit_ping=True)
            conn = None

            try:
                conn = zk.connect()
                conn.disable_device()
                attendances_unfiltered = conn.get_attendance()

                asistencias_por_empleado = {}
                for asistencia in attendances_unfiltered:
                    if asistencia.punch != 255:
                        continue

                    if asistencia.timestamp.year != anio_actual:
                        continue

                    user_id = asistencia.user_id
                    if user_id not in asistencias_por_empleado:
                        asistencias_por_empleado[user_id] = []
                    asistencias_por_empleado[user_id].append(asistencia)

                for user_id, attendances in asistencias_por_empleado.items():
                    employee_id = self.env['hr.employee'].search([('zknumber', '=', str(user_id))], limit=1)
                    if not employee_id:
                        continue

                    attendances.sort(key=lambda x: x.timestamp)

                    for attendance in attendances:
                        date_orig = tz.localize(attendance.timestamp).astimezone(pytz.UTC)
                        date = date_orig.astimezone(pytz.UTC)  # Asegurar UTC

                        _logger.warning(
                            f"📌 Procesando asistencia: {employee_id.name} - {date.strftime('%Y-%m-%d %H:%M:%S')}")

                        # 🔹 Buscar si ya existe esta asistencia como check_in o check_out
                        existing_attendance = attendance_obj.search([
                            ('employee_id', '=', employee_id.id),
                            '|',
                            ('check_in', '=', date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                            ('check_out', '=', date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                        ], limit=1)

                        if existing_attendance:
                            _logger.warning(
                                f"❌ IGNORANDO duplicado: {employee_id.name} - {date.strftime('%Y-%m-%d %H:%M:%S')}")
                            continue

                            # 🔹 Buscar el último check_in válido según el horario
                        last_attendance = attendance_obj.search([
                            ('employee_id', '=', employee_id.id),
                            ('check_out', '=', False),
                            ('check_in', '>=', (date - timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')),
                            ('check_in', '<=', date.strftime('%Y-%m-%d 23:59:59'))
                        ], order='check_in asc', limit=1)

                        if last_attendance:
                            _logger.warning(f"📌 Último check_in encontrado: {last_attendance.check_in}")

                            # Asegurar comparación de tiempo correcta
                            check_in_dt = last_attendance.check_in.replace(tzinfo=None)
                            date_naive = date.replace(tzinfo=None)

                            if self.can_unify_attendance(employee_id, date_naive, check_in_dt):
                                _logger.warning(
                                    f"✅ UNIFICANDO asistencia: {employee_id.name} - {check_in_dt.strftime('%Y-%m-%d %H:%M:%S')} --> {date_naive.strftime('%Y-%m-%d %H:%M:%S')}")
                                last_attendance.write(
                                    {'check_out': date_naive.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                            else:
                                _logger.warning(
                                    f"⚠️ CREANDO NUEVO registro para {employee_id.name} (No se pudo unir por horario)")
                                attendance_obj.create({
                                    'employee_id': employee_id.id,
                                    'check_in': date_naive.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                    'machine_id': machine.id,
                                })
                        else:
                            _logger.warning(
                                f"🔹 CREANDO NUEVO check_in para {employee_id.name} (No hay registros previos en el mismo día o día anterior)")
                            attendance_obj.create({
                                'employee_id': employee_id.id,
                                'check_in': date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'machine_id': machine.id,
                            })

            except Exception as e:
                _logger.error("Error al conectar con el dispositivo: %s" % e)
                raise UserError('La conexión no se ha logrado: %s' % (e))
            finally:
                if conn:
                    conn.enable_device()
                    conn.disconnect()

    def download_attendance(self):
        """ Método principal que descarga y procesa TODAS las asistencias """
        _logger.warning(" Ejecutando DESCARGA COMPLETA de asistencia")

        # Ejecutar la descarga de punch 255
        self.download_attendance_255()

        # Ejecutar la descarga de punch 0, 1, 4, 5
        self.download_attendance_0_1()

    @api.model
    def download_attendances_from_active_machines(self):
        active_machines = self.search([('activo', '=', True)])
        for machine in active_machines:
            machine.download_attendance()  # o cualquier otro método que desees ejecutar


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    check_in = fields.Datetime(string="Check In", default='', required=False)
    machine_id = fields.Many2one('zk.machine', string="Reloj Asociado")

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ This method is intentionally left blank to disable the check. """
        pass

    def name_get(self):
        # raise ValidationError('TEST')
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((attendance.id, _("%(empl_name)s from %(check_in)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(attendance,
                                                                                            fields.Datetime.from_string(
                                                                                                attendance.check_in))),
                }))
            else:
                if attendance.check_in:
                    result.append((attendance.id, _("%(empl_name)s from %(check_in)s to %(check_out)s") % {
                        'empl_name': attendance.employee_id.name,
                        'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(attendance,
                                                                                                fields.Datetime.from_string(
                                                                                                    attendance.check_in))),
                        'check_out': fields.Datetime.to_string(fields.Datetime.context_timestamp(attendance,
                                                                                                 fields.Datetime.from_string(
                                                                                                     attendance.check_out))),
                    }))
                else:
                    result.append((attendance.id, _("%(empl_name)s from %(check_in)s to %(check_out)s") % {
                        'empl_name': attendance.employee_id.name,
                        'check_in': 'Undefined',
                        'check_out': fields.Datetime.to_string(fields.Datetime.context_timestamp(attendance,
                                                                                                 fields.Datetime.from_string(
                                                                                                     attendance.check_out))),
                    }))
        return result

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        pass


class hrEmployee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    zk_location_line_ids = fields.One2many('zk.employee.location.line', 'employee_id', string='Locations')
    zknumber = fields.Char("Number zk")

    def delete_employee_zk(self):
        machine_id = self.env['zk.machine'].search([('id', '=', int(self.env.context.get('machine_id')))])
        machine_ip = machine_id.name
        port = machine_id.port
        zk = ZK(machine_ip, port=port, timeout=10, password=0, force_udp=False, ommit_ping=True)
        conn = ''
        try:
            conn = zk.connect()
            conn.disable_device()
            employee_location_line = self.env['zk.employee.location.line'].search(
                [('employee_id', '=', self.id), ('machine_id', '=', machine_id.id)])
            conn.delete_user(uid=employee_location_line.uid)
            machine_id.employee_ids = machine_id.employee_ids - self
            employee_location_line.unlink()
        except Exception as e:
            raise UserError('Unable to complete user registration')
        finally:
            if conn != '':
                conn.enable_device()
                conn.disconnect()
        return True

    def disassociate_employee_zk(self):
        machine_id = self.env['zk.machine'].search([('id', '=', int(self.env.context.get('machine_id')))])
        employee_location_line = self.env['zk.employee.location.line'].search(
            [('employee_id', '=', self.id), ('machine_id', '=', machine_id.id)])
        machine_id.employee_ids = machine_id.employee_ids - self
        employee_location_line.unlink()
        return True


class hrZkEmployeeLocationLine(models.Model):
    _name = 'zk.employee.location.line'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    zk_num = fields.Integer(string="ZKSoftware Number", help="ZK Attendance User Code", required=True)
    machine_id = fields.Many2one('zk.machine', string="Machine", required=True)
    location_id = fields.Many2one('zk.machine.location', related='machine_id.location_id', string="Location")
    uid = fields.Integer('Uid')

    _sql_constraints = [('unique_location_emp', 'unique(employee_id,location_id)',
                         'There is a record of this employee for this location.')]