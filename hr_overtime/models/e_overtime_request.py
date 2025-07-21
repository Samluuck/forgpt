# -*- coding: utf-8 -*-
from dateutil import relativedelta
import pandas as pd
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.resource.models.resource import HOURS_PER_DAY
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class HrOverTime(models.Model):
    _name = 'hr.overtime'
    _description = "HR Overtime"
    _inherit = ['mail.thread']

    def _get_employee_domain(self):
        """
        Define qué empleados puede seleccionar el usuario actual - Versión mejorada
        """
        current_user = self.env.user
        
        # RRHH y Administradores ven todos los empleados
        if (current_user.has_group('hr_documenta.rrhh_responsable2') or 
            current_user.has_group('hr.group_hr_manager')):
            return []  # Sin restricción
        
        # Para usuarios básicos, calcular IDs específicos
        try:
            current_employee = self.env['hr.employee'].search([('user_id', '=', current_user.id)], limit=1)
            
            if not current_employee:
                # Si no tiene empleado asociado, solo puede ver empleados con su usuario
                return [('user_id', '=', current_user.id)]
            
            allowed_ids = []
            
            # 1. Siempre puede seleccionarse a sí mismo
            allowed_ids.append(current_employee.id)
            
            # 2. Buscar empleados donde es aprobador (con y sin usuario)
            all_employees = self.env['hr.employee'].search([])
            for emp in all_employees:
                if current_employee.id in emp.aprobador_hhee.ids:
                    allowed_ids.append(emp.id)
            
            # 3. Subordinados directos
            direct_reports = self.env['hr.employee'].search([('parent_id', '=', current_employee.id)])
            allowed_ids.extend(direct_reports.ids)
            
            # Eliminar duplicados
            allowed_ids = list(set(allowed_ids))
            
            return [('id', 'in', allowed_ids)]
            
        except Exception as e:
            # En caso de error, ser conservador
            return [('user_id', '=', current_user.id)]

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.onchange('days_no_tmp')
    def _onchange_days_no_tmp(self):
        self.days_no = self.days_no_tmp

    name = fields.Char('Name', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado',
                              domain=_get_employee_domain, 
                              default=lambda self: self.env.user.employee_id.id, 
                              required=True)
    department_id = fields.Many2one('hr.department', string="Departamento",
                                related="employee_id.department_id", store=True)
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
                                compute='_compute_contract_id', store=True)
    
    date_from = fields.Datetime('Fecha inicio')
    date_to = fields.Datetime('Fecha fin')
    days_no_tmp = fields.Float('Hours', compute="_get_days", store=True)
    days_no = fields.Float('No. of Days', store=True)
    desc = fields.Text('Description', required=True)
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('ready', 'Listo para Configurar'),
            ('f_approve', 'En espera de Aprobación'),
            ('approved', 'Aprobado'),
            ('refused', 'Rechazado')
        ],
        string="Estado", default="draft"
    )

    cancel_reason = fields.Text('Refuse Reason')
    leave_id = fields.Many2one('hr.leave.allocation',
                               string="Leave ID")
    attchd_copy = fields.Binary('Adjuntar un archivo')
    attchd_copy_name = fields.Char('File Name')
    type = fields.Selection([('cash', 'Remunerado'), ('leave', 'Licencia')], default="cash", required=True, string="Tipo")
    overtime_type_id = fields.Many2one(
        'overtime.type',
        string='Tipo de Horas Extras',
        domain="[('type', '=', type), ('duration_type', '=', duration_type)]"
    )

    domingo = fields.Selection(
        [('yes', 'Sí'), ('no', 'No')],
        string='Es un día Domingo',
        compute="_compute_domingo",
        store=True,
        readonly=True,
        default='no'
    )
    public_holiday = fields.Selection(
        [('yes', 'Sí'), ('no', 'No')],
        string='Es un día feriado',
        readonly=True,
        store=True,
        default='no'
    )
    attendance_ids = fields.Many2many('hr.attendance', string='Attendance')
    work_schedule = fields.One2many(
        related='employee_id.resource_calendar_id.attendance_ids')
    global_leaves = fields.One2many(
        related='employee_id.resource_calendar_id.global_leave_ids')
    duration_type = fields.Selection([('hours', 'Horas'), ('days', 'Dias')], string="Tipo de duracion", default="hours",
                                     required=True)
    cash_hrs_amount = fields.Float(string='Overtime Amount', compute="_compute_overtime_hours", store=True, readonly=True)
    cash_day_amount = fields.Float(string='Overtime Amount', readonly=True)
    payslip_paid = fields.Boolean('Pagado en la nomina', readonly=True)
    # Campo relacionado para múltiples aprobadores
    aprobador_hhee = fields.Many2many(
        'hr.employee',
        string='Aprobadores de HHEE',
        related='employee_id.aprobador_hhee',
        readonly=True,
        store=False
    )
    ready_to_approve = fields.Boolean('Listo para Aprobar', default=False, readonly=True)

    @api.depends('employee_id')
    def _compute_contract_id(self):
        for record in self:
            if record.employee_id:
                # Usar sudo() para acceder al contrato sin problemas de permisos
                contract = record.employee_id.sudo().contract_id
                record.contract_id = contract.id if contract else False
            else:
                record.contract_id = False

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
                
                # Calcular diferencia total en segundos
                delta = finish_dt - start_dt
                total_seconds = delta.total_seconds()
                
                # Convertir a horas con decimales
                total_hours = total_seconds / 3600.0  # 3600 segundos = 1 hora
                
                # Para días: dividir por horas por día (usando HOURS_PER_DAY del módulo resource)
                total_days = total_hours / HOURS_PER_DAY
                
                sheet.update({
                    'days_no_tmp': total_hours if sheet.duration_type == 'hours' else total_days,
                })

    @api.depends('overtime_type_id', 'date_from', 'date_to', 'contract_id', 'cash_hrs_diurnal_amount', 'cash_hrs_nocturnal_amount')
    def _compute_overtime_hours(self):
        """ Calcula el monto total sumando los montos de horas extra diurnas y nocturnas. """
        for record in self:
            record.cash_hrs_amount = 0.0

            if not all([record.overtime_type_id, record.date_from, record.date_to, record.contract_id]):
                continue

            total_amount = record.cash_hrs_diurnal_amount + record.cash_hrs_nocturnal_amount
            record.cash_hrs_amount = total_amount

            
    diurnal_hours = fields.Float(string='Horas Extra Diurnas 50%', compute="_compute_diurnal_hours", store=True, readonly=True)
    nocturnal_hours = fields.Float(string='Horas Extra Nocturnas 100%', compute="_compute_nocturnal_hours", store=True, readonly=True)
    cash_hrs_diurnal_amount = fields.Float(string='Monto Horas Diurnas', compute="_compute_diurnal_hours", store=True, readonly=True)
    cash_hrs_nocturnal_amount = fields.Float(string='Monto Horas Nocturnas', compute="_compute_nocturnal_hours", store=True, readonly=True)

    @api.depends('overtime_type_id', 'date_from', 'date_to', 'contract_id', 'overtime_type_id.rule_line_ids')
    def _compute_diurnal_hours(self):
        """ Calcula las horas extra diurnas y su monto basándose en los rangos horarios. """
        for record in self:
            record.diurnal_hours = 0.0
            record.cash_hrs_diurnal_amount = 0.0

            if not all([record.overtime_type_id, record.date_from, record.date_to, record.contract_id]):
                continue

            # USAR SUDO() para acceder al contrato
            contract = record.contract_id.sudo()
            over_hour = contract.over_hour or 1.0

            start_dt = record.date_from - relativedelta.relativedelta(hours=3)
            end_dt = record.date_to - relativedelta.relativedelta(hours=3)

            duration = (end_dt - start_dt).total_seconds() / 3600.0
            if duration <= 0:
                continue

            start_hour = start_dt.hour + (start_dt.minute / 60.0)
            end_hour = end_dt.hour + (end_dt.minute / 60.0)

            if end_dt.date() != start_dt.date():
                end_hour += 24.0 * (end_dt.date() - start_dt.date()).days

            total_diurnal_hours = 0.0
            total_diurnal_amount = 0.0

            for rule in record.overtime_type_id.rule_line_ids:
                if rule.rule_type != 'diurnal':
                    continue

                rule_start = rule.from_hrs
                rule_end = rule.to_hrs
                multiplicador = rule.hrs_amount

                if start_dt.weekday() == 5:
                    adjusted_rule_start = self._convert_time_to_float("08:00")
                    adjusted_rule_end = self._convert_time_to_float("20:00")
                else:
                    adjusted_rule_start = rule_start
                    adjusted_rule_end = rule_end

                adjusted_start_hour = start_hour
                adjusted_end_hour = end_hour

                if rule_end < rule_start:
                    adjusted_rule_end += 24.0
                    if start_hour < rule_start:
                        adjusted_start_hour += 24.0
                    if end_hour < rule_start:
                        adjusted_end_hour += 24.0

                overlap_start = max(adjusted_start_hour, adjusted_rule_start)
                overlap_end = min(adjusted_end_hour, adjusted_rule_end)

                if overlap_end > overlap_start:
                    hours_in_range = overlap_end - overlap_start
                    total_diurnal_hours += hours_in_range
                    total_diurnal_amount += hours_in_range * multiplicador * over_hour

            record.diurnal_hours = total_diurnal_hours
            record.cash_hrs_diurnal_amount = total_diurnal_amount

    @api.depends('overtime_type_id', 'date_from', 'date_to', 'contract_id', 'overtime_type_id.rule_line_ids')
    def _compute_nocturnal_hours(self):
        """ Calcula las horas extra nocturnas y su monto basándose en los rangos horarios. """
        for record in self:
            record.nocturnal_hours = 0.0
            record.cash_hrs_nocturnal_amount = 0.0

            if not all([record.overtime_type_id, record.date_from, record.date_to, record.contract_id]):
                continue

            # USAR SUDO() para acceder al contrato
            contract = record.contract_id.sudo()
            if not contract.over_hour:
                continue

            over_hour = contract.over_hour

            start_dt = record.date_from - relativedelta.relativedelta(hours=3)
            end_dt = record.date_to - relativedelta.relativedelta(hours=3)

            duration = (end_dt - start_dt).total_seconds() / 3600.0
            if duration <= 0:
                continue

            start_hour = start_dt.hour + (start_dt.minute / 60.0)
            end_hour = end_dt.hour + (end_dt.minute / 60.0)

            if end_dt.date() != start_dt.date():
                end_hour += 24.0 * (end_dt.date() - start_dt.date()).days

            total_nocturnal_hours = 0.0
            total_nocturnal_amount = 0.0

            for rule in record.overtime_type_id.rule_line_ids:
                if rule.rule_type != 'nocturnal':
                    continue

                rule_start = rule.from_hrs
                rule_end = rule.to_hrs
                multiplicador = rule.hrs_amount

                if start_dt.weekday() == 5:
                    adjusted_rule_start = self._convert_time_to_float("20:00")
                    adjusted_rule_end = rule_end
                else:
                    adjusted_rule_start = rule_start
                    adjusted_rule_end = rule_end

                adjusted_start_hour = start_hour
                adjusted_end_hour = end_hour

                if rule_end < rule_start:
                    adjusted_rule_end += 24.0
                    if start_hour < rule_start:
                        adjusted_start_hour += 24.0
                    if end_hour < rule_start:
                        adjusted_end_hour += 24.0

                overlap_start = max(adjusted_start_hour, adjusted_rule_start)
                overlap_end = min(adjusted_end_hour, adjusted_rule_end)

                if overlap_end > overlap_start:
                    hours_in_range = overlap_end - overlap_start
                    total_nocturnal_hours += hours_in_range
                    total_nocturnal_amount += hours_in_range * multiplicador * over_hour

            record.nocturnal_hours = total_nocturnal_hours
            record.cash_hrs_nocturnal_amount = total_nocturnal_amount

    def _convert_time_to_float(self, time_str):
        """Convierte una hora con formato 'HH:MM' en un número flotante (Ej: '17:30' → 17.5)."""
        hours, minutes = map(int, time_str.split(':'))
        return hours + minutes / 60.0
    
    def submit_to_f(self):
        """Registra la solicitud y la envía automáticamente a 'ready' para configuración de RRHH"""
        for record in self:
            # Validaciones básicas
            if not record.date_from or not record.date_to:
                raise UserError(_('Debe especificar las fechas de inicio y fin.'))
            
            if not record.desc:
                raise UserError(_('Debe proporcionar una descripción del trabajo realizado.'))
            
            # Notificación al empleado
            recipient_partners = [(4, record.current_user.partner_id.id)]
            body = "Your OverTime Request is now pending configuration and approval..."
            msg = _(body)
            
            # TODAS las solicitudes van a 'ready' para que RRHH configure el tipo
            record.sudo().write({'state': 'ready'})
            
            # Notificar a RRHH sobre nueva solicitud pendiente de configuración
            rrhh_users = self.env.ref('hr_documenta.rrhh_responsable2').users
            hr_manager_users = self.env.ref('hr.group_hr_manager').users
            all_rrhh_users = rrhh_users | hr_manager_users
            
            for user in all_rrhh_users:
                if user.partner_id:
                    record.message_post(
                        body=f"Nueva solicitud de {record.employee_id.name} pendiente de configuración.",
                        partner_ids=[user.partner_id.id]
                    )
        
        return True

    def mark_ready_to_approve(self):
        """Marca la solicitud como lista para aprobar (solo RRHH/Admin)"""
        for record in self:
            # Verificar permisos
            if not (record.env.user.has_group('hr_documenta.rrhh_responsable2') or 
                    record.env.user.has_group('hr.group_hr_manager')):
                raise UserError(_('Solo RRHH y Administradores pueden marcar solicitudes como listas para aprobar.'))
            
            # Validar que esté en estado correcto
            if record.state != 'ready':
                raise UserError(_('Solo se pueden marcar como "Listo para Aprobar" las solicitudes en estado "Listo para Configurar".'))
            
            # Validar que tenga tipo configurado
            if not record.overtime_type_id:
                raise UserError(_('Debe seleccionar un tipo de horas extras antes de marcar como listo para aprobar.'))
            
            # Cambiar estado
            record.write({
                'state': 'f_approve',
                'ready_to_approve': True
            })
            
            # Notificar a los aprobadores
            record._notify_approvers()

    def _notify_approvers(self):
        """Notifica a los aprobadores que hay una solicitud pendiente"""
        for record in self:
            approvers = record._get_all_approvers()
            if approvers:
                partner_ids = [user.partner_id.id for user in approvers if user.partner_id]
                if partner_ids:
                    record.message_post(
                        body=f"Solicitud de {record.employee_id.name} lista para aprobación.",
                        partner_ids=partner_ids
                    )

    def _get_all_approvers(self):
        """Obtiene todos los usuarios que pueden aprobar esta solicitud"""
        approvers = self.env['res.users']
        
        # RRHH y Administradores siempre pueden aprobar
        rrhh_users = self.env.ref('hr_documenta.rrhh_responsable2').users
        hr_manager_users = self.env.ref('hr.group_hr_manager').users
        approvers |= rrhh_users | hr_manager_users
        
        # Aprobadores asignados específicamente
        if self.employee_id.aprobador_hhee:
            assigned_approvers = self.employee_id.aprobador_hhee.mapped('user_id').filtered(lambda u: u)
            approvers |= assigned_approvers
        
        # Gerente directo (parent_id)
        if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
            approvers |= self.employee_id.parent_id.user_id
        
        return approvers

    def _can_approve_overtime(self):
        """Verifica si el usuario actual puede aprobar/rechazar esta solicitud"""
        current_user = self.env.user
        
        # Solo RRHH_RESPONSABLE2 y HR_MANAGER siempre pueden aprobar
        if (current_user.has_group('hr_documenta.rrhh_responsable2') or 
            current_user.has_group('hr.group_hr_manager')):
            return True
        
        # Verificar si es uno de los aprobadores asignados
        if self.employee_id.aprobador_hhee:
            aprobador_users = self.employee_id.aprobador_hhee.mapped('user_id')
            if current_user in aprobador_users:
                return True
        
        # Verificar si es el gerente/jefe directo (parent_id)
        if (self.employee_id.parent_id and 
            self.employee_id.parent_id.user_id and 
            self.employee_id.parent_id.user_id.id == current_user.id):
            return True
        
        return False

    def _can_self_approve(self):
        """Verifica si el usuario puede aprobar su propia solicitud"""
        current_user = self.env.user
        
        # RRHH y Administradores pueden aprobar sus propias solicitudes
        if (current_user.has_group('hr_documenta.rrhh_responsable2') or 
            current_user.has_group('hr.group_hr_manager')):
            return True
        
        # Verificar si es su propia solicitud
        if self.employee_id.user_id and self.employee_id.user_id.id == current_user.id:
            return False  # No puede auto-aprobar (excepto RRHH/Admin arriba)
        
        return True  # Puede aprobar solicitudes de otros

    def approve(self):
        """Aprueba la solicitud con validación de permisos de aprobador"""
        for record in self:
            # Verificar que esté en estado correcto
            if record.state != 'f_approve':
                raise UserError(_('Solo se pueden aprobar solicitudes en estado "En espera de Aprobación".'))
            
            # Verificar permisos de aprobación
            if not record._can_approve_overtime():
                raise UserError(_('No tienes permisos para aprobar esta solicitud de horas extras.'))
            
            # Verificar auto-aprobación
            if not record._can_self_approve():
                raise UserError(_('No puedes aprobar tu propia solicitud de horas extras.'))
            
            if record.overtime_type_id.type == 'leave':
                # Verificar que se tenga un tipo de ausencia configurado
                if not record.overtime_type_id.leave_type:
                    raise UserError(_('El tipo de hora extra debe tener un tipo de ausencia configurado.'))

                # Calcular la cantidad de días o horas para la asignación
                if record.duration_type == 'days':
                    number_of_days = record.days_no_tmp
                else:  # duration_type == 'hours'
                    number_of_days = record.days_no_tmp / HOURS_PER_DAY

                # Crear la asignación de licencia
                holiday_vals = {
                    'name': 'Overtime Allocation',
                    'holiday_status_id': record.overtime_type_id.leave_type.id,
                    'number_of_days': number_of_days,
                    'notes': record.desc,
                    'holiday_type': 'employee',
                    'employee_id': record.employee_id.id,
                    'state': 'validate',
                }
                holiday = self.env['hr.leave.allocation'].sudo().create(holiday_vals)
                record.leave_id = holiday.id

            # Notificar al usuario
            if record.current_user and record.current_user.partner_id:
                record.message_post(
                    body="Your Time In Lieu Request Has been Approved ...",
                    partner_ids=[record.current_user.partner_id.id]
                )

            # Actualizar el estado a 'approved'
            record.state = 'approved'

    def reject(self):
        """Rechaza la solicitud con validación de permisos de aprobador"""
        for record in self:
            # Verificar que esté en estado correcto
            if record.state != 'f_approve':
                raise UserError(_('Solo se pueden rechazar solicitudes en estado "En espera de Aprobación".'))
            
            # Verificar permisos de aprobación
            if not record._can_approve_overtime():
                raise UserError(_('No tienes permisos para rechazar esta solicitud de horas extras.'))
            
            # Notificar al usuario
            if record.current_user and record.current_user.partner_id:
                record.message_post(
                    body="Your Overtime Request has been rejected.",
                    partner_ids=[record.current_user.partner_id.id]
                )
        
            record.state = 'refused'
            
    def reject_from_approved(self):
        """Rechaza la solicitud desde estado aprobado - Solo RRHH y Administradores"""
        for record in self:
            # Verificar que esté en estado correcto
            if record.state != 'approved':
                raise UserError(_('Solo se pueden rechazar solicitudes en estado "Aprobado".'))
            
            # Verificar permisos - Solo RRHH y Administradores
            if not (record.env.user.has_group('hr_documenta.rrhh_responsable2') or 
                    record.env.user.has_group('hr.group_hr_manager')):
                raise UserError(_('Solo RRHH y Administradores pueden rechazar solicitudes aprobadas.'))
            
            # Si tenía una asignación de licencia, eliminarla
            if record.leave_id:
                record.leave_id.sudo().unlink()
                record.leave_id = False
            
            # Notificar al usuario
            if record.current_user and record.current_user.partner_id:
                record.message_post(
                    body="Su solicitud de horas extras aprobada ha sido rechazada por RRHH/Administración.",
                    partner_ids=[record.current_user.partner_id.id]
                )
        
            record.state = 'refused'

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
            # Solo permite cambiar a borrador desde rechazado
            if record.state == 'refused':
                record.state = 'draft'
                record.overtime_type_id = False  # Limpiar tipo para reconfigurar
                record.ready_to_approve = False  # Reset del flag
            else:
                raise UserError(_('Solo puedes pasar a borrador si la solicitud se encuentra rechazada.'))

    @api.model
    def create(self, values):
        """Override create para permitir que aprobadores creen solicitudes para sus empleados asignados"""
        
        # Si es RRHH/Admin, permitir sin restricciones
        if (self.env.user.has_group('hr_documenta.rrhh_responsable2') or 
            self.env.user.has_group('hr.group_hr_manager')):
            return super(HrOverTime, self).create(values)
        
        # Verificar permisos para crear solicitud
        employee_id = values.get('employee_id')
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            
            # Verificar si puede crear solicitud para este empleado
            can_create = False
            
            # 1. Puede crear para sí mismo
            if employee.user_id and employee.user_id.id == self.env.user.id:
                can_create = True
            
            # 2. Puede crear si es aprobador asignado
            elif current_employee and current_employee in employee.aprobador_hhee:
                can_create = True
            
            # 3. Puede crear si es gerente directo
            elif current_employee and employee.parent_id and employee.parent_id.id == current_employee.id:
                can_create = True
            
            if not can_create:
                raise UserError(_('No tienes permisos para crear solicitudes de horas extras para este empleado.'))
        
        # Llamar al método create original
        record = super(HrOverTime, self).create(values)

        # Resto de la lógica original (asistencias)
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
        _logger.info("Entrando a _onchange_date. Fecha inicio: %s, Fecha fin: %s, Empleado: %s",
                     self.date_from, self.date_to, self.employee_id.name)

        holiday = 'no'
        if self.contract_id and self.date_from and self.date_to:
            contract = self.contract_id.sudo()
            for leaves in contract.resource_calendar_id.global_leave_ids:
                leave_dates = pd.date_range(leaves.date_from, leaves.date_to).date
                overtime_dates = pd.date_range(self.date_from, self.date_to).date
                for over_time in overtime_dates:
                    if over_time in leave_dates:
                        holiday = 'yes'
                        break

        self.public_holiday = holiday

    @api.depends('date_from')
    def _compute_domingo(self):
        """ Calcula si la fecha seleccionada cae en un domingo. """
        for record in self:
            if record.date_from:
                date_value = fields.Datetime.from_string(record.date_from)
                weekday = date_value.weekday()

                # LOG para verificar la fecha y el día de la semana
                _logger.info(f"*** Verificando si {date_value} es domingo. Día de la semana: {weekday} ***")

                if weekday == 6:  # En Python, 6 representa domingo
                    record.domingo = 'yes'
                else:
                    record.domingo = 'no'
            else:
                record.domingo = 'no'


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

    # Cambio de Float a Time
    from_hrs = fields.Float('Desde (Hora)', required=True, help="Hora de inicio en formato 24H (Ej: 17:00)")
    to_hrs = fields.Float('Hasta (Hora)', required=True, help="Hora de fin en formato 24H (Ej: 20:00)")

    hrs_amount = fields.Float('Multiplicador', required=True,
                              help="Factor multiplicador para calcular el monto de horas extras.")
    rule_type = fields.Selection([
        ('diurnal', 'Diurna'),
        ('nocturnal', 'Nocturna'),
    ], string='Tipo de Regla', required=True, default='diurnal', help="Indica si esta regla corresponde a horas extra diurnas o nocturnas.")
    
    def _convert_float_to_time(self, float_time):
        """ Convierte un número flotante (Ej: 17.5) en una hora con formato (Ej: 17:30). """
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return "{:02d}:{:02d}".format(hours, minutes)