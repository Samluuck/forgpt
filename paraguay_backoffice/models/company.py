# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import date

class ResCompany(models.Model):
    _inherit = "res.company"

    ruc = fields.Char(required=True, string="RUC")
    dv =  fields.Char(size=1,required=True, string="DV")
    nombrefantasia = fields.Char(string="Nombre de fantasia")
    razon_social = fields.Char(string="Razon Social")
    representante_legal = fields.Char(string="Representante Legal")
    ruc_representante = fields.Char(string="RUC del Rep. Legal")
    dv_representante = fields.Char(required=True, string="DV del Representante Legal")
    jornal = fields.Monetary(string="Jornal diario vigente")
    exportador = fields.Boolean(string="Es exportador?")

    diario_caja_chica = fields.Many2one('account.journal',string="Diario de Caja Chica")



    def compute_fiscalyear_dates(self, current_date):
        if not current_date:
            current_date = date.today()
        res = super(ResCompany,self).compute_fiscalyear_dates(current_date)
        return res

    @api.onchange('ruc','dv')
    def setear_vat(self):
        if self.ruc and self.dv:
            self.vat = self.ruc + '-' + self.dv
