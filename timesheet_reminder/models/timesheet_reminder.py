from odoo import models, api, fields
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class TimesheetReminder(models.TransientModel):
    _name = 'timesheet.reminder'
    _description = 'Recordatorio de Timesheet'

    @api.model
    def send_daily_reminder(self):
        """Envía recordatorio diario a usuarios del grupo"""
        try:
            # Buscar el grupo de recordatorio timesheet
            group = self.env.ref('timesheet_reminder.group_timesheet_reminder', raise_if_not_found=False)
            
            if not group:
                _logger.warning("Grupo 'group_timesheet_reminder' no encontrado")
                return
            
            # Solo ejecutar en días laborables (lunes a viernes)
            today = datetime.now()
            if today.weekday() >= 5:  # 5=sábado, 6=domingo
                return
            
            # Usuarios activos del grupo
            users = group.users.filtered(lambda u: u.active)
            
            for user in users:
                try:
                    # Crear notificación en el chatter del usuario
                    self._create_notification(user)
                    
                    # Crear actividad pendiente
                    self._create_activity(user)
                    
                    _logger.info(f"Recordatorio enviado a {user.name}")
                    
                except Exception as e:
                    _logger.error(f"Error enviando recordatorio a {user.name}: {str(e)}")
                    
        except Exception as e:
            _logger.error(f"Error en send_daily_reminder: {str(e)}")

    def _create_notification(self, user):
        """Crear notificación en conversaciones"""
        # Buscar o crear canal de notificaciones
        channel = self.env['mail.channel'].sudo().search([
            ('name', '=', f'Recordatorio Timesheet - {user.name}'),
            ('channel_type', '=', 'chat')
        ], limit=1)
        
        if not channel:
            channel = self.env['mail.channel'].sudo().create({
                'name': f'Recordatorio Timesheet - {user.name}',
                'channel_type': 'chat',
                'channel_partner_ids': [(4, user.partner_id.id)],
            })
        
        # Enviar mensaje al canal
        channel.sudo().message_post(
            body=f"🕒 <b>Recordatorio Timesheet</b><br/>"
                 f"Hola {user.name},<br/>"
                 f"No olvides cargar tus horas trabajadas en el timesheet de hoy.<br/>"
                 f"<i>Mensaje automático enviado el {fields.Date.today()}</i>",
            message_type='notification',
            subtype_xmlid='mail.mt_comment'
        )

    def _create_activity(self, user):
        """Crear actividad recordatorio"""
        # Verificar si ya existe una actividad pendiente para hoy
        existing_activity = self.env['mail.activity'].search([
            ('res_model', '=', 'res.users'),
            ('res_id', '=', user.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Recordatorio Timesheet'),
            ('date_deadline', '=', fields.Date.today()),
        ], limit=1)
        
        if existing_activity:
            return  # Ya existe recordatorio para hoy
        
        # Obtener tipo de actividad por defecto
        activity_type = self.env['mail.activity.type'].search([
            ('name', 'ilike', 'To Do')
        ], limit=1)
        
        if not activity_type:
            activity_type = self.env['mail.activity.type'].search([], limit=1)
        
        self.env['mail.activity'].sudo().create({
            'activity_type_id': activity_type.id if activity_type else 1,
            'summary': '⏰ Recordatorio: Cargar Timesheet',
            'note': f'Recordatorio automático para cargar las horas trabajadas en el timesheet del día {fields.Date.today()}',
            'res_model': 'res.users',
            'res_id': user.id,
            'user_id': user.id,
            'date_deadline': fields.Date.today(),
        })