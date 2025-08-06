# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import datetime



class Anexo5_datos_entidad(models.Model):
    _name='anexo5_datos_entidad'

    codigo=fields.Char()
    name=fields.Char()
    texto = fields.Html()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")


class Anexo5_base_preparacion(models.Model):
    _name='anexo5_base_preparacion'


    codigo=fields.Char()
    name=fields.Char()
    texto = fields.Html()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_politicas_contables(models.Model):
    _name='anexo5_politicas_contables'


    codigo=fields.Char()
    name=fields.Char()
    texto = fields.Html()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_rentas_exentas(models.Model):
    _name='anexo5_rentas_exentas'


    codigo=fields.Char()
    name=fields.Char()
    texto = fields.Text()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_identificacion_partes(models.Model):
    _name = 'anexo5_identificacion_partes'

    codigo = fields.Char()
    name = fields.Char()
    texto = fields.Text()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_hechos_posteriores(models.Model):
    _name = 'anexo5_hechos_posteriores'

    codigo = fields.Char()
    name = fields.Char()
    texto = fields.Text()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_otras_notas(models.Model):
    _name = 'anexo5_otras_notas'

    codigo = fields.Char()
    name = fields.Char()
    texto = fields.Text()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")

class Anexo5_cuentas_patrimoniales(models.Model):
    _name='anexo5_cuentas_patrimoniales'

    texto_inicial=fields.Html()
    cuenta_ids=fields.Many2many('account.account')
    texto_final=fields.Html()
    anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")
    empresa=fields.Boolean(string='Agrupar por Empressa')