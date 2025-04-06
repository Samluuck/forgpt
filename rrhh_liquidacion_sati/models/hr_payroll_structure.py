from odoo import fields, models, api


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    es_liquidacion_despido = fields.Boolean(default=False,string='Es Liquidacion Despido?',help="Marca esta opción en caso de que sea una liquidación de despido")
    es_liquidacion_despido_injustificado = fields.Boolean(default=False,string='Es Liquidacion Despido Injustificado?',help="Marca esta opción en caso de que sea una liquidación de despido injustifiado")
    es_liquidacion_renuncia = fields.Boolean(default=False,string='Es Liquidacion Renuncia?',help="Marca esta opción en caso de que sea una liquidación de Renuncia")


