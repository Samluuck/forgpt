from odoo import api, fields, models, tools, _, exceptions
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta,date


class HrCautionsType(models.Model):
    _name = 'hr.cautions.type'
    _description = 'Tipos de Amonestaciones'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(string="Nombre del tipo de amonestación",required=True)
    gravity = fields.Integer(string="Gravedad para el tipo de amonestación")
    articles = fields.Text(string="Artículos de referencia y subpárrafos", help="Artículos y fracciones conforme al código de trabajo vigente")

class HrCautions(models.Model):
    _name = 'hr.cautions'
    _description = 'Amonetaciones'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Número de amonestación", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    caution_type_id = fields.Many2one('hr.cautions.type', string="Tipo de Amonestación", required=True)
    date = fields.Date(string="Fecha", required=True)
    reported = fields.Boolean(string="Reportada", help="Marcar en caso de que el aviso haya sido comunicado a los organismos correspondientes")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], tracking=True)  # Habilitamos el tracking
    documento_apoyo = fields.Binary(string="Documento de Apoyo de la Amonestación", attachment=True)



    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            seq = self.env['ir.sequence'].next_by_code('hr.caution.code') or '/'
            rec.name = seq


    def action_draft(self):
        for rec in self:
            if not rec.reported:
                rec.state = 'draft'
            else:
                raise ValidationError(_('Cannot set draft reported cautions'))