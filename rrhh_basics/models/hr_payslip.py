from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
import logging
from datetime import datetime, timedelta
import babel
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)


class HrPayslipInh(models.Model):
    _inherit = "hr.payslip"

    dias_trabajados = fields.Integer(string="Días Trabajados", compute='_compute_dias_trabajados')
    employee_type = fields.Char(string='Tipo de Empleado')
    department = fields.Char(string='Departamento')

    def setValues(self):
        for rec in self:
            rec.department = rec.employee_id.department_id.name

    def get_month_name(self):
        ttyme = datetime.combine(fields.Date.from_string(self.date_from), datetime.min.time())
        locale = self.env.context.get('lang') or 'en_US'
        return tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM', locale=locale)).capitalize()

    def get_payslip_inputs(self):
        for rec in self:
            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue
            lista_diccionario = []

            # Buscar entradas de ingresos y descuentos
            inputs = self.env['hr.income.expense'].search([
                ('date_from', '=', rec.date_from),
                ('date_to', '<=', rec.date_to),
                ('employee_id', '=', rec.employee_id.id)
            ])

            for i in inputs:
                # Asegúrate de que 'i.code' tenga un valor válido
                if not i.code:
                    raise ValidationError("El campo 'code' no puede estar vacío.")

                # Corregir acceso al código en el Many2one
                input_type = self.env['hr.payslip.input.type'].search([('code', '=', i.code.code)], limit=1)
                if input_type:
                    data = {
                        'name': i.name,
                        'code': i.code.code,  # Accede al valor del código
                        'amount': i.amount,
                        'sequence': 10,
                        'input_type_id': input_type.id,
                        'contract_id': rec.contract_id.id,
                        'payslip_id': rec.id,
                    }
                    lista_diccionario.append(data)
                else:
                    raise ValidationError(f"No se ha encontrado otra entrada con el código {i.code.code}")

            # Crear entradas en el modelo 'hr.payslip.input'
            entrada = self.env['hr.payslip.input'].browse([])
            for r in lista_diccionario:
                entrada += entrada.new(r)
            rec.input_line_ids = entrada

    def compute_sheet(self):
        for rec in self:
            rec.get_payslip_inputs()
            rec._compute_worked_days_line_ids()
            super(HrPayslipInh, rec).compute_sheet()

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        """
        Sobreescribir el método para ejecutar diferentes cálculos de días trabajados
        dependiendo del valor del campo `asis_marc` en el contrato.
        """
        for payslip in self:
            if payslip.contract_id and payslip.date_from and payslip.date_to:
                # Limpiar las líneas de días trabajados actuales
                payslip.worked_days_line_ids = [(5, 0, 0)]

                # Verificar si el campo 'asis_marc' está marcado en el contrato
                if payslip.contract_id.asis_marc:
                    # Usar la lógica basada en asistencias
                    worked_days_lines = self.get_worked_day_lines_by_attendance(
                        payslip.contract_id, payslip.date_from, payslip.date_to)
                else:
                    # Usar la lógica estándar de work entries y días fuera de contrato
                    super(HrPayslipInh, self)._compute_worked_days_line_ids()
                    worked_days_lines = [{
                        'name': wd.name,
                        'sequence': wd.sequence,
                        'code': wd.code,
                        'number_of_days': wd.number_of_days,
                        'number_of_hours': wd.number_of_hours,
                        'contract_id': wd.contract_id.id,
                        'work_entry_type_id': wd.work_entry_type_id.id,
                        'amount': wd.amount,
                    } for wd in payslip.worked_days_line_ids]

                    # Agregar fines de semana a las líneas de días trabajados
                    total_days = (payslip.date_to - payslip.date_from).days + 1
                    weekends = self._get_weekends(payslip.date_from, payslip.date_to)
                    for worked_day in worked_days_lines:
                        if worked_day['code'] == 'WORK100':
                            worked_day['number_of_days'] += weekends

                # Crear nuevas líneas de días trabajados
                worked_days_lines_obj = self.env['hr.payslip.worked_days'].browse([])
                for line in worked_days_lines:
                    worked_days_lines_obj += worked_days_lines_obj.new(line)
                payslip.worked_days_line_ids = worked_days_lines_obj

    def get_worked_day_lines_by_attendance(self, contract, date_from, date_to):
        """
        Obtener las asistencias en el período de la nómina y calcular los días trabajados.
        Solo se contará una asistencia por día, sin importar cuántas entradas y salidas haya.
        """
        worked_days_lines = []

        # Buscar el tipo de entrada de trabajo para las asistencias usando el código 'WORK100'
        attendance_work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1)

        if not attendance_work_entry_type:
            raise ValidationError(_('No se encontró el tipo de entrada de trabajo para "Attendance".'))

        # Obtener las asistencias del empleado en el período de la nómina
        round_days_mode = attendance_work_entry_type.round_days_type
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('check_in', '>=', date_from),
            ('check_out', '<=', date_to)
        ])

        total_days = 0
        total_hours = 0
        days_processed = set()  # Mantendrá un registro de los días ya procesados

        for attendance in attendances:
            if attendance.check_in and attendance.check_out:
                check_in_date = fields.Date.to_date(attendance.check_in)
                worked_time = attendance.check_out - attendance.check_in
                hours_worked = worked_time.total_seconds() / 3600.0

                if round_days_mode == 'completo':
                    if check_in_date not in days_processed:
                        total_days += 1
                        days_processed.add(check_in_date)
                else:
                    total_hours += hours_worked
                    if check_in_date not in days_processed:
                        total_days += 1
                        days_processed.add(check_in_date)
        # Crear la entrada de días trabajados y horas reales trabajadas
        worked_days_lines.append({
            'name': 'Días trabajados (basado en asistencias)',
            'sequence': 1,
            'code': 'WORK100',
            'number_of_days': total_days,
            'number_of_hours': total_hours,
            'contract_id': contract.id,
            'work_entry_type_id': attendance_work_entry_type.id,
            'amount': 0.0,
        })

        _logger.info(f"Asistencias procesadas con opción {round_days_mode}: {worked_days_lines}")
        return worked_days_lines

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_dias_trabajados(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                total_days = (rec.date_to - rec.date_from).days + 1
                weekends = rec._get_weekends(rec.date_from, rec.date_to)
                rec.dias_trabajados = total_days + weekends - (total_days - weekends) % 30

    def _get_weekends(self, date_from, date_to):
        """
        Calcula los fines de semana (sábado y domingo) en el período de contrato,
        **saltando** días en los que el empleado tiene **ausencias completas** (por día).
        """
        total_weekends = 0

        for record in self:
            contract = record.contract_id
            if not contract:
                continue

            # Si el contrato tiene daily_wage definido, no contar fines de semana
            if hasattr(contract, 'daily_wage') and contract.daily_wage:
                continue

            contract_start = max(contract.date_start or date_from, date_from)
            contract_end = min(contract.date_end or date_to, date_to)
            resource_calendar = contract.resource_calendar_id

            # ---------------------------------------
            # 1) Construir el conjunto de días ausentes (por día, NO por horas)
            # ---------------------------------------
            absent_days = set()
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'validate'),
                ('request_unit_hours', '=', False),  # <-- Filtra ausencias completas
                ('request_date_from', '<=', contract_end),
                ('request_date_to', '>=', contract_start),
            ])

            for leave in leaves:
                start_day = max(leave.request_date_from, contract_start)
                end_day = min(leave.request_date_to, contract_end)

                # Si estos campos son tipo date o datetime, asegúrate de normalizar a date
                # Suponiendo que request_date_from/to son tipo date:
                current_absence = start_day
                while current_absence <= end_day:
                    absent_days.add(current_absence)
                    current_absence += timedelta(days=1)

            # ---------------------------------------
            # 2) Recorrer cada día del período y saltar ausencias
            # ---------------------------------------
            sabado = 0
            domingo = 0
            current_date = contract_start

            while current_date <= contract_end:
                # Si es un día ausente, no se cuenta
                if current_date in absent_days:
                    current_date += timedelta(days=1)
                    continue

                weekday = current_date.weekday()
                # sábado => weekday=5
                if weekday == 5:
                    # Verificamos que en el calendario de asistencia NO se trabaje sábados
                    if not any(a.dayofweek == '5' for a in resource_calendar.attendance_ids):
                        sabado += 1
                # domingo => weekday=6
                if weekday == 6:
                    if not any(a.dayofweek == '6' for a in resource_calendar.attendance_ids):
                        domingo += 1

                current_date += timedelta(days=1)

            total_weekends += sabado + domingo

        return total_weekends

    def _get_new_worked_days_lines(self):
        if self.struct_id.use_worked_day_lines:
            return [(5, 0, 0)] + [(0, 0, vals) for vals in self._get_worked_day_lines()]
        return [(5, 0, 0)]

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        Calcula las líneas de días trabajados incluyendo días fuera del contrato.
        """
        res = []
        self.ensure_one()
        contract = self.contract_id

        # Verificar que el contrato tenga un calendario asignado
        if not contract.resource_calendar_id:
            raise ValidationError("El contrato no tiene asignado un calendario de recursos.")

        resource_calendar = contract.resource_calendar_id

        # Obtener las líneas de días trabajados estándar
        res = self._get_worked_day_lines_values(domain=domain)
        if not check_out_of_contract:
            return res

        out_days, out_hours = 0, 0

        # Cálculo de días fuera del contrato al inicio
        if self.date_from < contract.date_start:
            # Diferencia en días antes de que comience el contrato
            out_days = (contract.date_start - self.date_from).days
            out_hours = out_days * 24  # Horas fuera del contrato, suponiendo 24 horas por día

        # Cálculo de días fuera del contrato al final
        if contract.date_end and contract.date_end < self.date_to:
            start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
            stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)

            # Usar el calendario para calcular los días y horas fuera del contrato
            out_time = resource_calendar.get_work_duration_data(
                start, stop, compute_leaves=False,
                domain=['|', ('work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)]
            )
            out_days += out_time['days']
            out_hours += out_time['hours']

        # Si se encontraron días u horas fuera del contrato, añadirlos a las líneas
        if out_days or out_hours:
            work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
            res.append({
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type.id,
                'number_of_days': out_days,
                'number_of_hours': out_hours,
            })

        return res

# class HrWorkEntryType(models.Model):
#     _inherit = "hr.work.entry.type"
#
#     round_days_type = fields.Selection(
#         selection_add=[('completo', 'Días Completos')],
#         default='completo'
#     )

class HrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    round_days_type = fields.Selection(
        selection_add=[('completo', 'Días Completos')],
        ondelete={'completo': 'set default'},  # Se pasa correctamente como diccionario
        default='completo'
    )
