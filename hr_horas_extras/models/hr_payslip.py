from odoo import models, fields, api

class HrPayslipInherited(models.Model):
    _inherit = 'hr.payslip'

    horas_diurnas_total = fields.Float(string="Total Horas Extras Diurnas", compute='_compute_horas_extras', store=True)
    horas_nocturnas_total = fields.Float(string="Total Horas Extras Nocturnas", compute='_compute_horas_extras', store=True)
    horas_domifer_total = fields.Float(string="Total Horas Extras Domingos/Feriados", compute='_compute_horas_extras', store=True)
    total_late_minutes = fields.Float(string="Total de Minutos Tardíos", compute='_compute_horas_extras', store=True)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_horas_extras(self):
        for payslip in self:
            # Asegúrate de que las fechas están definidas
            if not payslip.date_from or not payslip.date_to:
                payslip.horas_diurnas_total = 0
                payslip.horas_nocturnas_total = 0
                payslip.horas_domifer_total = 0
                payslip.total_late_minutes = 0
                continue

            # Filtrar las asistencias estrictamente dentro del rango de fechas
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('check_in', '>=', payslip.date_from),  # entradas a partir o posterior de la fecha 'desde' en la nomina
                ('check_out', '<=', payslip.date_to)  # Salidas anteriores o igual de la fecha 'hasta' en la nomina
            ]) if payslip.employee_id else []

            # Verifica si el empleado tiene permitido cobrar horas extras
            if payslip.employee_id and not payslip.employee_id.cobra_horas_extras:
                # Si no puede cobrar horas extras, establece los totales en 0
                payslip.horas_diurnas_total = 0
                payslip.horas_nocturnas_total = 0
                payslip.horas_domifer_total = 0
            else:
                # Si puede cobrar horas extras, realiza el cálculo normal
                total_horas_diurnas = sum(attendance.horas_diurnas for attendance in attendances)
                total_horas_nocturnas = sum(attendance.horas_nocturnas for attendance in attendances)
                total_horas_domifer = sum(attendance.horas_domifer for attendance in attendances)

                payslip.horas_diurnas_total = total_horas_diurnas
                payslip.horas_nocturnas_total = total_horas_nocturnas
                payslip.horas_domifer_total = total_horas_domifer

            # Calcula los minutos de llegada tardía, independientemente de `cobra_horas_extras`
            total_late = sum(attendance.late_check_in for attendance in attendances if attendance.late_check_in)
            payslip.total_late_minutes = total_late
