# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from dateutil.parser import parse
from odoo.exceptions import ValidationError
import time
import logging
import pytz

_logger = logging.getLogger(__name__)


class HrLeaveTypeInh(models.Model):
    _inherit = "hr.leave.type"

    es_vacacion = fields.Boolean(string='Es una ausencia de tipo Vacación',required=False,help="Tildar esto en caso de que la ausencia sea de tipo vacaciones, Importante para el reporte de sueldos y jornales")
    es_ausencia_maternidad = fields.Boolean(string='Es Maternidad',required=False)
    es_ausencia_no_pagada_corrida=fields.Boolean(string='Es Ausencia No Pagada en dias corridos?',help="Marcar en caso de que la ausencia sea una ausencia que se toma en dias corridos")



    @api.constrains('es_ausencia_no_pagada_corrida')
    def _check_unique_es_ausencia_no_pagada_corrida(self):
        if self.es_ausencia_no_pagada_corrida:
            existing = self.search([
                ('id', '!=', self.id),
                ('es_ausencia_no_pagada_corrida', '=', True)
            ])
            if existing:
                raise ValidationError(
                    "Ya existe un tipo de ausencia marcado como 'Es Ausencia No Pagada en dias corridos'. Solo puede haber uno.")