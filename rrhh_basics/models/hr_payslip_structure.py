from odoo import fields, models, api

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'
    dias_trabajados=fields.Boolean(default=False,string="Dias Trabajados",help="Marca para que se cuenten los dias como trabajados")
    es_aguinaldo = fields.Boolean(default=False,string='Es Aguinaldo?',help="Marca esta opción en caso de que sea un aguinaldo")
    es_mensualero = fields.Boolean(default=False,string='Es Mensualero?',help="Marca esta opción en caso de que sea un mensualero")
    es_jornalero = fields.Boolean(default=False,string='Es Jornalero?',help="Marca esta opción en caso de que sea un jornalero")
    es_comisionista = fields.Boolean(default=False,string='Es comisionista?',help="Marca esta opción en caso de que sea una comision")