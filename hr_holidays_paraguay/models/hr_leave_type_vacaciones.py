from odoo import models, fields, api
from odoo.exceptions import ValidationError





class HrHolidaysStatus(models.Model):
    _inherit = 'hr.leave.type'

    es_vacaciones = fields.Boolean(string="Vacaciones",help="Marcar en caso que este tipo de ausencia sea Vacaciones")
    es_cumpleaños =  fields.Boolean(string="Cumpleaños",help="Marcar en caso que este tipo de ausencia sea Cumpleaños")
    adelanto_vacaciones = fields.Boolean(string="Adelanto de Vacaciones", help="Marcar en caso que este tipo de ausencia sea Adelanto de Vacaciones")

    def _verificar_tipo_vacaciones(self):
        print("######################### Entra en _verificar_tipo_vacaciones #############################")
        for rec in self:
            tipo_vacaciones = self.env['hr.leave.type'].sudo().search_count([
                ('es_vacaciones', '=', True),
                ('company_id', '=', rec.company_id.id)
            ])
            if tipo_vacaciones > 1:
                raise ValidationError('Ya existe un tipo de ausencia "Vacaciones" para la compañía')
    def _verificar_tipo_cumpleaños(self):
        print("######################### Entra en _verificar_tipo_cumpleaños #############################")
        for rec in self:
            tipo_vacaciones = self.env['hr.leave.type'].sudo().search_count([
                ('es_cumpleaños', '=', True),
                ('company_id', '=', rec.company_id.id)
            ])
            if tipo_vacaciones > 1:
                raise ValidationError('Ya existe un tipo de ausencia "Cumpleaños" para la compañía')
    def _verificar_tipo_adelanto_vacaciones(self):
        for rec in self:
            tipo_vacaciones = self.env['hr.leave.type'].sudo().search_count([
                ('adelanto_vacaciones', '=', True),
                ('company_id', '=', rec.company_id.id)
            ])
            if tipo_vacaciones > 1:
                raise ValidationError('Ya existe un tipo de ausencia "Adelanto de Vacaciones" para la compañía')