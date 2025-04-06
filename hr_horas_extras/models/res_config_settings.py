from odoo import models, fields, api
import datetime

class LateCheckinSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuración de la hora en formato de cadena (HH:MM)
    horario_diurno = fields.Char(string="Inicio de Horas Extras Diurnas",
                                 config_parameter='hr_horas_extras.horario_diurno',

                                 )
    horas_nocturnas = fields.Char(string="Inicio de Horas Extras Nocturnas",
                                  config_parameter='hr_horas_extras.horas_nocturnas',
                                  default='00:00')

    tolerancia_llegada_tardia = fields.Integer(
        string="Tolerancia Llegada Tardía (Minutos)",
        config_parameter='hr_horas_extras.tolerancia_llegada_tardia',
        default=0
    )
    tolerancia_llegada_anticipada = fields.Integer(
        string="Legada anticipada en (Minutos)",
        config_parameter='hr_horas_extras.tolerancia_llegada_anticipada',
        default=0
    )



    def set_values(self):
        res = super(LateCheckinSettings, self).set_values()
        # Guardar la configuración en el formato correcto
        self.env['ir.config_parameter'].sudo().set_param('hr_horas_extras.horario_diurno', self.horario_diurno)
        self.env['ir.config_parameter'].sudo().set_param('hr_horas_extras.horas_nocturnas', self.horas_nocturnas)
        self.env['ir.config_parameter'].sudo().set_param('hr_horas_extras.tolerancia_llegada_tardia', self.tolerancia_llegada_tardia)
        self.env['ir.config_parameter'].sudo().set_param('hr_horas_extras.tolerancia_llegada_anticipada', self.tolerancia_llegada_anticipada)

        return res

    @api.model
    def get_values(self):
        res = super(LateCheckinSettings, self).get_values()
        # Obtener la configuración en el formato correcto
        res.update(
            horario_diurno=self.env['ir.config_parameter'].sudo().get_param('hr_horas_extras.horario_diurno', '18:30'),
            horas_nocturnas=self.env['ir.config_parameter'].sudo().get_param('hr_horas_extras.horas_nocturnas','00:00'),
            tolerancia_llegada_tardia=int(self.env['ir.config_parameter'].sudo().get_param('hr_horas_extras.tolerancia_llegada_tardia', 0)),)

        return res
