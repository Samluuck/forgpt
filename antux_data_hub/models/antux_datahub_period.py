from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AntuxDataHubPeriod(models.Model):
    _name = 'antux.datahub.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Data Hub - Período'
    _order = 'date_from desc'

    name = fields.Char(
        string='Período',
        required=True,
        tracking=True
    )

    date_from = fields.Date(
        string='Desde',
        required=True,
        tracking=True
    )

    date_to = fields.Date(
        string='Hasta',
        required=True,
           tracking=True
    )

    active = fields.Boolean(
        default=True,
        tracking=True
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """
        Valida la coherencia cronológica del periodo definido.

        Esta función garantiza que la fecha de inicio ('Desde') no sea posterior a la 
        fecha de finalización ('Hasta'). Al mantener esta integridad, se previenen 
        errores lógicos en el procesamiento de datos y en la generación de informes 
        que dependen de rangos temporales válidos.

        Raises:
            ValidationError: Si la fecha de inicio es mayor que la fecha de fin.
        """
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(
                    'La fecha de inicio "Desde" (%s) no puede ser posterior '
                    'a la fecha de finalización "Hasta" (%s).' % (record.date_from, record.date_to)
                )
