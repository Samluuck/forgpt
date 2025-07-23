# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_despacho_admin = fields.Boolean(
        string='Administrador General de Despachos',
        default=False,
        help="Otorga acceso completo a configuraciones y administración del módulo de despachos"
    )

    @api.model
    def create(self, vals):
        user = super().create(vals)
        if vals.get('is_despacho_admin'):
            user._update_despacho_admin_group()
        return user

    def write(self, vals):
        res = super().write(vals)
        if 'is_despacho_admin' in vals:
            self._update_despacho_admin_group()
        return res

    def _update_despacho_admin_group(self):
        """Actualiza la pertenencia al grupo según el checkbox"""
        admin_group = self.env.ref('despacho.group_despacho_admin')
        for user in self:
            if user.is_despacho_admin:
                admin_group.users = [(4, user.id)]
            else:
                admin_group.users = [(3, user.id)]