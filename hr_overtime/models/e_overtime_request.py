# -*- coding: utf-8 -*-
from dateutil import relativedelta
import pandas as pd
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.resource.models.resource import HOURS_PER_DAY
import logging
_logger = logging.getLogger(__name__)


class HrOverTime(models.Model):
    _name = 'hr.overtime'
    _description = "HR Overtime"
    _inherit = ['mail.thread']

    def _get_employee_domain(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1)
        domain = [('id', '=', employee.id)]
        if self.env.user.has_group('hr.group_hr_user'):
            domain = []
        return domain

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.onchange('days_no_tmp')
    def _onchange_days_no_tmp(self):
        self.days_no = self.days_no_tmp

    name = fields.Char('Name', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado',
                                  domain=_get_employee_domain, default=lambda self: self.env.user.employee_id.id, required=True)
    department_id = fields.Many2one('hr.department', string="Departamento",
                                    related="employee_id.department_id")
    job_id = fields.Many2one('hr.job', string="Puesto de trabajo", related="employee_id.job_id")
    manager_id = fields.Many2one('res.users', string="Supervisor",
                                 related="employee_id.parent_id.user_id", store=True)
    current_user = fields.Many2one('res.users', string="Current User",
                                   related='employee_id.user_id',
                                   default=lambda self: self.env.uid,
                                   store=True)
    current_user_boolean = fields.Boolean()
    project_id = fields.Many2one('project.project', string="Project")
    project_manager_id = fields.Many2one('res.users', string="Project Manager")
    contract_id = fields.Many2one('hr.contract', string="Contrato",
                                  related="employee_id.contract_id",
                                  )
    date_from = fields.Datetime('Fecha inicio')
    date_to = fields.Datetime('Fecha fin')
    days_no_tmp = fields.Float('Hours', compute="_get_days", store=True)
    days_no = fields.Float('No. of Days', store=True)
    desc = fields.Text('Description', required=True)
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('f_approve', 'En espera'),
            ('approved', 'Aprobado'),
            ('refused', 'Rechazado')
        ],
        string="Estado", default="draft"
    )

    type = fields.Selection(
        [
            ('cash', 'Remunerado'),
            ('leave', 'Licencia')
        ],
        string="Tipo de hora extra"
    )


    cancel_reason = fields.Text('Refuse Reason')
    leave_id = fields.Many2one('hr.leave.allocation',
                               string="Leave ID")
    attchd_copy = fields.Binary('Adjuntar un archivo')
    attchd_copy_name = fields.Char('File Name')
    type = fields.Selection([('cash', 'Remunerado'), ('leave', 'Licencia')], default="leave", required=True, string="Tipo")
    overtime_type_id = fields.Many2one('overtime.type', domain="[('type','=',type),('duration_type','=', "
                                                               "duration_type)]")
    public_holiday = fields.Char(string='Feriado', readonly=True)
    attendance_ids = fields.Many2many('hr.attendance', string='Attendance')
    work_schedule = fields.One2many(
        related='employee_id.resource_calendar_id.attendance_ids')
    global_leaves = fields.One2many(
        related='employee_id.resource_calendar_id.global_leave_ids')
    duration_type = fields.Selection([('hours', 'Horas'), ('days', 'Dias')], string="Tipo de duracion", default="hours",
                                     required=True)
    cash_hrs_amount = fields.Float(string='Overtime Amount', readonly=True)
    cash_day_amount = fields.Float(string='Overtime Amount', readonly=True)
    payslip_paid = fields.Boolean('Pagado en la nomina', readonly=True)

    @api.onchange('employee_id')
    def _get_defaults(self):
        for sheet in self:
            if sheet.employee_id:
                sheet.update({
                    'department_id': sheet.employee_id.department_id.id,
                    'job_id': sheet.employee_id.job_id.id,
                    'manager_id': sheet.sudo().employee_id.parent_id.user_id.id,
                })

    @api.depends('project_id')
    def _get_project_manager(self):
        for sheet in self:
            if sheet.project_id:
                sheet.update({
                    'project_manager_id': sheet.project_id.user_id.id,
                })

    @api.depends('date_from', 'date_to')
    def _get_days(self):
        for recd in self:
            if recd.date_from and recd.date_to:
                if recd.date_from > recd.date_to:
                    raise ValidationError('La fecha de inicio debe ser menor que la fecha de finalización')
        for sheet in self:
            if sheet.date_from and sheet.date_to:
                start_dt = fields.Datetime.from_string(sheet.date_from)
                finish_dt = fields.Datetime.from_string(sheet.date_to)
                s = finish_dt - start_dt
                difference = relativedelta.relativedelta(finish_dt, start_dt)
                hours = difference.hours
                minutes = difference.minutes
                days_in_mins = s.days * 24 * 60
                hours_in_mins = hours * 60
                days_no = ((days_in_mins + hours_in_mins + minutes) / (24 * 60))

                diff = sheet.date_to - sheet.date_from
                days, seconds = diff.days, diff.seconds
                hours = days * 24 + seconds // 3600
                sheet.update({
                    'days_no_tmp': hours if sheet.duration_type == 'hours' else days_no,
                })

    @api.onchange('overtime_type_id')
    def _get_hour_amount(self):
        if self.overtime_type_id.rule_line_ids and self.duration_type == 'hours':
            for recd in self.overtime_type_id.rule_line_ids:
                if recd.from_hrs < self.days_no_tmp <= recd.to_hrs and self.contract_id:
                    if self.contract_id.over_hour:
                        cash_amount = self.contract_id.over_hour * recd.hrs_amount
                        self.cash_hrs_amount = cash_amount
                    else:
                        raise UserError(_("Se necesita que este cargado el campo de salario por hora en el contrato del empleado."))
        elif self.overtime_type_id.rule_line_ids and self.duration_type == 'days':
            for recd in self.overtime_type_id.rule_line_ids:
                if recd.from_hrs < self.days_no_tmp <= recd.to_hrs and self.contract_id:
                    if self.contract_id.over_day:
                        cash_amount = self.contract_id.over_day * recd.hrs_amount
                        self.cash_day_amount = cash_amount
                    else:
                        raise UserError(_("Se necesita que este cargado el campo de salario por dia en el contrato del empleado."))


    def submit_to_f(self):
        # notification to employee
        recipient_partners = [(4, self.current_user.partner_id.id)]
        body = "Your OverTime Request Waiting Finance Approve .."
        msg = _(body)

        # notification to finance :
        group = self.env.ref('account.group_account_invoice', False)
        recipient_partners = []

        body = "You Get New Time in Lieu Request From Employee : " + str(
            self.employee_id.name)
        msg = _(body)
        return self.sudo().write({
            'state': 'f_approve'
        })

    def approve(self):
        if self.overtime_type_id.type == 'leave':
            if self.duration_type == 'days':
                holiday_vals = {
                    'name': 'Overtime',
                    'holiday_status_id': self.overtime_type_id.leave_type.id,
                    'number_of_days': self.days_no_tmp,
                    'notes': self.desc,
                    'holiday_type': 'employee',
                    'employee_id': self.employee_id.id,
                    'state': 'validate',
                }
            else:
                day_hour = self.days_no_tmp / HOURS_PER_DAY
                holiday_vals = {
                    'name': 'Overtime',
                    'holiday_status_id': self.overtime_type_id.leave_type.id,
                    'number_of_days': day_hour,
                    'notes': self.desc,
                    'holiday_type': 'employee',
                    'employee_id': self.employee_id.id,
                    'state': 'validate',
                }
            holiday = self.env['hr.leave.allocation'].sudo().create(
                holiday_vals)
            self.leave_id = holiday.id

        # notification to employee :
        recipient_partners = [(4, self.current_user.partner_id.id)]
        body = "Your Time In Lieu Request Has been Approved ..."
        msg = _(body)
        return self.sudo().write({
            'state': 'approved',

        })

    def reject(self):

        self.state = 'refused'

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        for req in self:
            domain = [
                ('date_from', '<=', req.date_to),
                ('date_to', '>=', req.date_from),
                ('employee_id', '=', req.employee_id.id),
                ('id', '!=', req.id),
                ('state', 'not in', ['refused']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_(
                    'No es posible tener 2 solicitudes de horas extra que se superpongan en el mismo día'))

    def reset_to_draft(self):
        """
        Permite volver al estado Borrador desde Rechazado.
        """
        for record in self:
            #permite cambiar a borrador desde rechazado
            if record.state == 'refused':
                record.state = 'draft'
            else:
                raise UserError(_('solo puedes pasar a borrador si la solicitud se encuentra rechazada.'))

    @api.model
    def create(self, values):
        # Llamar al super para crear el registro
        record = super(HrOverTime, self).create(values)

        # Buscar y asignar asistencias si las fechas están definidas
        if 'date_from' in values and 'date_to' in values and 'employee_id' in values:
            hr_attendance = self.env['hr.attendance'].search(
                [('check_in', '>=', values['date_from']),
                 ('check_in', '<=', values['date_to']),
                 ('employee_id', '=', values['employee_id'])]
            )
            if hr_attendance:
                record.attendance_ids = [(6, 0, hr_attendance.ids)]

        return record

    def write(self, values):
        # Llamar al super para actualizar el registro
        result = super(HrOverTime, self).write(values)

        # Busca y asigna asistencias si las fechas cambian
        for record in self:
            if 'date_from' in values or 'date_to' in values or 'employee_id' in values:
                date_from = values.get('date_from', record.date_from)
                date_to = values.get('date_to', record.date_to)
                employee_id = values.get('employee_id', record.employee_id.id)
                hr_attendance = self.env['hr.attendance'].search(
                    [('check_in', '>=', date_from),
                     ('check_in', '<=', date_to),
                     ('employee_id', '=', employee_id)]
                )
                if hr_attendance:
                    record.attendance_ids = [(6, 0, hr_attendance.ids)]

        return result

    def unlink(self):
        for overtime in self.filtered(
                lambda overtime: overtime.state != 'draft'):
            raise UserError(
                _('No se puede eliminar una solicitud que no esté en estado de borrador.'))
        return super(HrOverTime, self).unlink()

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_date(self):
        _logger.info("Entrando a _onchange_date. Fecha inicio: %s, Fecha fin: %s, Empleado: %s", self.date_from,
                     self.date_to, self.employee_id.name)

        holiday = False
        if self.contract_id and self.date_from and self.date_to:
            for leaves in self.contract_id.resource_calendar_id.global_leave_ids:
                leave_dates = pd.date_range(leaves.date_from, leaves.date_to).date
                overtime_dates = pd.date_range(self.date_from, self.date_to).date
                for over_time in overtime_dates:
                    for leave_date in leave_dates:
                        if leave_date == over_time:
                            holiday = True
            if holiday:
                self.public_holiday = 'Tienes días feriados en tu solicitud de horas extras..'
            else:
                self.public_holiday = ' '


class HrOverTimeType(models.Model):
    _name = 'overtime.type'
    _description = "HR Overtime Type"

    name = fields.Char('Nombre')
    type = fields.Selection(
        [
            ('cash', 'Remunerado'),
            ('leave', 'Licencia')
        ],
        string="Tipo de hora extra"
    )

    duration_type = fields.Selection([('hours', 'Horas'), ('days', 'Dias')], string="Tipo de duracion", default="hours",
                                     required=True)
    leave_type = fields.Many2one('hr.leave.type', string='Tipo de ausencia', domain="[('id', 'in', leave_compute)]")
    leave_compute = fields.Many2many('hr.leave.type', compute="_get_leave_type")
    rule_line_ids = fields.One2many('overtime.type.rule', 'type_line_id')

    @api.onchange('duration_type')
    def _get_leave_type(self):
        dur = ''
        ids = []
        if self.duration_type:
            if self.duration_type == 'days':
                dur = 'day'
            else:
                dur = 'hour'
            leave_type = self.env['hr.leave.type'].search([('request_unit', '=', dur)])
            for recd in leave_type:
                ids.append(recd.id)
            self.leave_compute = ids


class HrOverTimeTypeRule(models.Model):
    _name = 'overtime.type.rule'
    _description = "HR Overtime Type Rule"

    type_line_id = fields.Many2one('overtime.type', string='Over Time Type')
    name = fields.Char('Nombre', required=True)
    from_hrs = fields.Float('Desde', required=True)
    to_hrs = fields.Float('Hasta', required=True)
    hrs_amount = fields.Float('Porcentaje', required=True)
