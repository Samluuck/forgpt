from odoo import models, fields, api


class HrSalaryRules(models.Model):
    _inherit = 'hr.salary.rule'

    aguinaldo_set = fields.Boolean("Aguinaldo SET",help="Marque el campo para que el monto de esta regla figure en el reporte de la set")
    desc_jubi = fields.Boolean("Descuento jubilacion SET",help="Marque el campo para que el monto de esta regla figure en el reporte de la set")
    segu_social = fields.Boolean("Descuento por seguro social SET",help="Marque el campo para que el monto de esta regla figure en el reporte de la set")
    ot_desc = fields.Boolean("Otros descuentos SET",help="Marque el campo para que el monto de esta regla figure en el reporte de la set")
    bruto_set = fields.Boolean("Bruto sin descuentos SET",help="Marque el campo para que el monto de esta regla aparezca en el bruto de la set")