from odoo import models, fields, api

class HrEmployeeOvertime(models.Model):
    _inherit = 'hr.employee'

    aprobador_hhee = fields.Many2many(
        'hr.employee',
        'hr_employee_aprobador_rel',
        'employee_id',
        'aprobador_id',
        string='Aprobadores de Horas Extras',
        help='Empleados encargados de aprobar las solicitudes de horas extras de este empleado',
        domain="[('user_id', '!=', False)]",  # Solo empleados con usuario
        tracking=True
    )

    @api.onchange('aprobador_hhee')
    def _onchange_aprobador_hhee(self):
        """Validación para evitar auto-aprobación"""
        if self.aprobador_hhee and self.id in self.aprobador_hhee.ids:
            return {
                'warning': {
                    'title': 'Advertencia',
                    'message': 'Un empleado no puede ser su propio aprobador de horas extras.'
                }
            }

    def get_overtime_approvers(self):
        """
        Devuelve los usuarios que pueden aprobar horas extras para este empleado.
        Si no tiene aprobadores asignados, automáticamente devuelve RRHH y Administradores.
        """
        approvers = self.env['res.users']
        
        # 1. Aprobadores asignados específicamente
        if self.aprobador_hhee:
            assigned_approvers = self.aprobador_hhee.mapped('user_id').filtered(lambda u: u)
            approvers |= assigned_approvers
        
        # 2. Gerente directo (parent_id)
        if self.parent_id and self.parent_id.user_id:
            approvers |= self.parent_id.user_id
        
        # 3. Si no tiene aprobadores asignados, automáticamente RRHH y Administradores
        if not self.aprobador_hhee:
            try:
                rrhh_users = self.env.ref('hr_documenta.rrhh_responsable2').users
                hr_manager_users = self.env.ref('hr.group_hr_manager').users
                hr_user_users = self.env.ref('hr.group_hr_user').users
                approvers |= rrhh_users | hr_manager_users | hr_user_users
            except:
                # Si los grupos no existen, usar administradores por defecto
                admin_users = self.env.ref('base.group_system').users
                approvers |= admin_users
        
        # 4. RRHH y Administradores SIEMPRE pueden aprobar (incluso si tienen aprobadores asignados)
        try:
            rrhh_users = self.env.ref('hr_documenta.rrhh_responsable2').users
            hr_manager_users = self.env.ref('hr.group_hr_manager').users
            hr_user_users = self.env.ref('hr.group_hr_user').users
            approvers |= rrhh_users | hr_manager_users | hr_user_users
        except:
            pass
        
        return approvers

    def can_approve_overtime_for(self, employee_id):
        """
        Verifica si el usuario actual puede aprobar horas extras para un empleado específico.
        """
        if not employee_id:
            return False
        
        current_user = self.env.user
        employee = self.browse(employee_id) if isinstance(employee_id, int) else employee_id
        
        # RRHH y Administradores siempre pueden aprobar
        if (current_user.has_group('hr_documenta.rrhh_responsable2') or 
            current_user.has_group('hr.group_hr_manager') or
            current_user.has_group('hr.group_hr_user')):
            return True
        
        # Obtener empleado actual
        current_employee = self.search([('user_id', '=', current_user.id)], limit=1)
        if not current_employee:
            return False
        
        # Verificar si es aprobador asignado
        if current_employee in employee.aprobador_hhee:
            return True
        
        # Verificar si es gerente directo
        if employee.parent_id and employee.parent_id.id == current_employee.id:
            return True
        
        # Si no tiene aprobadores asignados, verificar si es RRHH/Admin
        if not employee.aprobador_hhee:
            return (current_user.has_group('hr_documenta.rrhh_responsable2') or 
                   current_user.has_group('hr.group_hr_manager') or
                   current_user.has_group('hr.group_hr_user'))
        
        return False