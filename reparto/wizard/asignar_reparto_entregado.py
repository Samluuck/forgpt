# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError





class asignar_reparto_wizard_entregado(models.TransientModel):

    _name = "wizard.asignar.reparto.entregado"


    @api.multi
    def procesar (self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        for reparto in self.env['delivery.order'].browse(active_ids):
            if reparto.state == 'entregado':
                raise ValidationError('Uno o mas de los repartos ya se encuentran en estado entregado')
            else:
                reparto.set_entregado()
