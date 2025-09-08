from odoo import models, api, fields
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class TimesheetReminder(models.TransientModel):
    _name = 'timesheet.reminder'
    _description = 'Recordatorio de Timesheet'

    @api.model
    def send_daily_reminder(self):
        """Envía recordatorio diario a usuarios del grupo (solo días hábiles)"""
        try:
            # 1) Grupo destino
            group = self.env.ref('timesheet_reminder.group_timesheet_reminder', raise_if_not_found=False)
            if not group:
                _logger.warning("Grupo 'group_timesheet_reminder' no encontrado")
                return

            # 2) Solo lunes–viernes
            if datetime.now().weekday() >= 5:  # 5=sábado, 6=domingo
                _logger.info("No se envían recordatorios en fin de semana")
                return

            # 3) Usuarios activos del grupo
            users = group.users.filtered(lambda u: u.active)
            if not users:
                _logger.info("No hay usuarios activos en el grupo")
                return

            _logger.info(f"Enviando recordatorios a {len(users)} usuarios")

            for user in users:
                try:
                    self._create_notification(user)   # única vía: Inbox + email
                    _logger.info(f"✅ Notificación+correo creada para {user.name}")
                except Exception as e:
                    _logger.error(f"❌ Error con {user.name}: {e}")

        except Exception as e:
            _logger.error(f"❌ Error en send_daily_reminder: {e}")

    def _create_notification(self, user):
        """Crea una notificación visible en Inbox y envía email (una sola acción)."""
        author_partner = self.env.ref('base.partner_root')

        ctx = dict(
            self.env.context,
            mail_post_autofollow=False,   # no autoseguimiento
            mail_notify_force_send=True,  # fuerza creación/envío de mail.mail
        )

        msg = user.partner_id.sudo().with_context(ctx).message_post(
            body=f'''
                <div style="padding:15px;background:#f0f8ff;border-left:4px solid #875A7B;border-radius:4px;">
                    <h4 style="color:#875A7B;margin:0 0 10px 0;">🕒 Recordatorio</h4>
                    <p style="margin:0 0 10px 0;">
                        Por favor no se olvide de realizar la carga de horas en <strong>PORTAL EMPLEADOS REGIER</strong>
                    </p>
                    <p style="font-size:12px;color:#666;margin:0;">
                        <em>Recordatorio automático - {fields.Date.today().strftime("%d/%m/%Y")} a las 16:30</em>
                    </p>
                </div>
            ''',
            subject="Parte de Horas",
            message_type='notification',                  # notificación → Inbox
            subtype_xmlid='mail.mt_comment',              # subtipo visible
            partner_ids=[user.partner_id.id],             # destinatario
            author_id=author_partner.id,                  # autor ≠ destinatario
            email_layout_xmlid='mail.mail_notification_light',  # plantilla email
        )

        # Fallback: si el cron de correo no corre, enviamos ya mismo
        mails = self.env['mail.mail'].sudo().search([('mail_message_id', '=', msg.id)])
        if mails:
            mails.send()
