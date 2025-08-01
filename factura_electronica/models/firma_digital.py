# -*- coding: utf-8 -*-
import io
import base64
from datetime import datetime

from odoo import models, fields, api,_
import logging
import tempfile
from zipfile import ZipFile
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
try:
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except ImportError:
    _logger.warning('Error en cargar crypto')

class FirmaDigital(models.Model):
    _name = 'firma.digital'
    _order='id desc'

    name=fields.Char()
    estado = fields.Selection(selection=[
        ('borrador', 'borrador'),
        ('activo', 'Activo'),
        ('expirado', 'expirado')
    ], string="State", default="borrador")
    file = fields.Binary(required=True)
    folder = fields.Char(string="Nombre de la Carpeta", required=True)
    date_start = fields.Datetime(string="Fecha Inicio",readonly=True)
    date_end = fields.Datetime(string="Fecha Fin",readonly=True)
    public_key = fields.Char(string="Public Key",readonly=False)
    private_key = fields.Char(string="Private Key",readonly=False)
    # cert = fields.Text(string='Certificate', readonly=True)
    # priv_key = fields.Text(string='Private Key', readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company.id
    )
    user_ids=fields.Many2many('res.users')



    def load_password_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Insert Password'),
            'res_model': 'certificate.pass',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.onchange('file','name')
    def _set_file_name(self):

        if self.name and self.file:
            name=self.name
            if  name.find('.pfx') <0 :
                raise UserError('El archivo no es compatible a un certificado')



    def pasar_borrador(self):
        self.date_start = None
        self.date_end = None
        self.estado = 'borrador'


