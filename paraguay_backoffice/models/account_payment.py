from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pago_colgado = fields.Boolean(
        string="Pago colgado")  # Campo que se puede ser actualizado vía importación excel a efectos de identificar pagos que quedaron sin facturas o para cualquier otro fin.

    @api.model
    def eliminar_pagos_colgados(self):
        # TODO: Función para eliminar aquellos pagos que tengan el campo "pago_colgado" como verdadero. Este campo se debe completar
        # previamente vía actualización a através de filtros
        for rec in self:
            if rec.pago_colgado:
                rec.action_draft()
                rec.unlink()
    def action_draft(self):
        super(AccountPayment, self).action_draft()
        self.move_id.posted_before = False
        self.move_id.name = '/'

