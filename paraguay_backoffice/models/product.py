# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError




class ProductTemplate(models.Model):
    _inherit = 'product.template'

    company_id = fields.Many2one(default=lambda self: self._get_default_company())

    @api.model
    def _get_default_company(self):

        compania_actual = self.env.company.id
        return compania_actual

    # funcion para verificar que no se dupliquen los codigos de referencia interna en el modelo 'product.template'

    @api.constrains('default_code')
    def unique_internal_reference(self):
        for record in self:
            if record.default_code:
                existing_product = record.env['product.template'].search(
                    [('id', '!=', record.id), ('default_code', '=', record.default_code)])
                if existing_product:
                    raise Warning("No puede tener el mismo código de referencia interna para dos productos")