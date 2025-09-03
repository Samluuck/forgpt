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
                _logger.info("No se envían recordatorios en fin de semana")
                return
            
            # Usuarios activos del grupo
            users = group.users.filtered(lambda u: u.active)
            
            if not users:
                _logger.warning("No se encontraron usuarios activos en el grupo")
                return
            
            _logger.info(f"Enviando recordatorios a {len(users)} usuarios")
            
            for user in users:
                try:
                    # Enviar EMAIL
                    if user.email:
                        self._send_email_reminder(user)
                        _logger.info(f"✅ Email enviado a {user.name} ({user.email})")
                    
                    # Crear NOTIFICACIÓN INTERNA
                    _logger.info(f"🔄 Intentando crear notificación para {user.name}")
                    self._create_notification(user)
                    _logger.info(f"✅ Notificación interna creada para {user.name}")
                    
                except Exception as e:
                    _logger.error(f"❌ Error enviando recordatorio a {user.name}: {str(e)}")
                    
        except Exception as e:
            _logger.error(f"❌ Error en send_daily_reminder: {str(e)}")

    def _create_notification(self, user):
        """Crear notificación interna en Odoo"""
        try:
            _logger.info(f"🔄 Creando notificación para usuario ID: {user.id}, Partner ID: {user.partner_id.id}")
            
            # Método 1: Mensaje directo al usuario (más visible)
            message = user.partner_id.message_post(
                body=f'''
                    <div style="padding: 15px; background: #f0f8ff; border-left: 4px solid #875A7B; border-radius: 4px;">
                        <h4 style="color: #875A7B; margin: 0 0 10px 0;">🕒 Recordatorio</h4>
                        <p style="margin: 0 0 10px 0;">
                            Por favor realizar la carga de horas en <strong>PORTAL EMPLEADOS REGIER</strong>
                        </p>
                        <p style="font-size: 12px; color: #666; margin: 0;">
                            <em>Recordatorio automático - {fields.Date.today().strftime('%d/%m/%Y')} a las 16:30</em>
                        </p>
                    </div>
                ''',
                subject="⏰ Recordatorio: Parte de Horas",
                message_type='comment',  # Cambio: comment en lugar de notification
                partner_ids=[user.partner_id.id],  # Agregar destinatario específico
                email_from=self.env.company.email or 'recordatorio@regier.com',
            )
            _logger.info(f"✅ Mensaje directo creado con ID: {message.id}")
            
            # Método 2: Crear notificación en bandeja de entrada
            self.env['mail.message'].sudo().create({
                'subject': '⏰ Recordatorio parte de horas',
                'body': f'Por favor no olvides de realizar tu carga de horas en el PORTAL EMPLEADOS REGIER del día {fields.Date.today().strftime("%d/%m/%Y")}',
                'message_type': 'notification',
                'partner_ids': [(4, user.partner_id.id)],
                'author_id': self.env.user.partner_id.id,
                'res_id': user.partner_id.id,
                'model': 'res.partner',
            })
            _logger.info(f"✅ Notificación en bandeja creada para {user.name}")
            
            # Método 3: Crear actividad (para que aparezca en "Actividades")
            self._create_activity(user)
            
        except Exception as e:
            _logger.error(f"❌ Error creando notificación para {user.name}: {str(e)}")

    def _create_activity(self, user):
        """Crear actividad adicional"""
        try:
            # Verificar si ya existe una actividad pendiente para hoy
            existing_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'res.users'),
                ('res_id', '=', user.id),
                ('user_id', '=', user.id),
                ('summary', 'ilike', 'Recordatorio Timesheet'),
                ('date_deadline', '=', fields.Date.today()),
            ], limit=1)
            
            if existing_activity:
                _logger.info(f"⚠️ Ya existe actividad para {user.name} hoy")
                return
            
            # Obtener modelo res.users
            res_model = self.env['ir.model'].search([('model', '=', 'res.users')], limit=1)
            
            # Obtener tipo de actividad
            activity_type = self.env['mail.activity.type'].search([
                ('name', 'ilike', 'To Do')
            ], limit=1)
            
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([], limit=1)
            
            activity = self.env['mail.activity'].sudo().create({
                'activity_type_id': activity_type.id if activity_type else 1,
                'summary': '⏰ Recordatorio Parte de Horas',
                'note': f'Por favor no te olvides de realizar tu carga de horas en el PORTAL EMPLEADOS REGIER del día {fields.Date.today().strftime("%d/%m/%Y")}',
                'res_model': 'res.users',
                'res_model_id': res_model.id,
                'res_id': user.id,
                'user_id': user.id,
                'date_deadline': fields.Date.today(),
            })
            _logger.info(f"✅ Actividad creada con ID: {activity.id}")
            
        except Exception as e:
            _logger.error(f"❌ Error creando actividad para {user.name}: {str(e)}")

    def _send_email_reminder(self, user):
        """Enviar email de recordatorio"""
        mail_values = {
            'subject': '⏰ Recordatorio: Parte de Horas',
            'body_html': f'''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #875A7B, #9B6B8A); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h2 style="margin: 0;">🕒 Recordatorio</h2>
                    </div>
                    
                    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p style="font-size: 16px; margin: 0 0 15px 0;">Hola <strong>{user.name}</strong>,</p>
                        
                        <p style="font-size: 16px; color: #333; margin: 15px 0;">
                            Por favor realizar la carga de horas en <strong style="color: #875A7B;">PORTAL EMPLEADOS REGIER</strong>.
                        </p>
                        
                        <p style="font-size: 14px; color: #666; margin: 15px 0;">
                            No olvides registrar todas las actividades del día de hoy.
                        </p>
                    </div>
                    
                    <div style="text-align: center; padding: 15px; background: #e8f4f8; border-radius: 8px;">
                        <p style="color: #666; font-size: 12px; margin: 0;">
                            <em>Mensaje automático enviado el {fields.Date.today().strftime('%d/%m/%Y')} a las 16:30</em>
                        </p>
                    </div>
                </div>
            ''',
            'email_to': user.email,
            'email_from': self.env.company.email or self.env.user.email or 'noreply@regier.com',
            'auto_delete': True,
        }
        
        # Crear y enviar el email
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()