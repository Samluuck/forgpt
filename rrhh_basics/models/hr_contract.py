from odoo import models, fields,api

class HrStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    # Agregar la opción "daily" al campo wage_type de Odoo
    wage_type = fields.Selection(
        selection_add=[('daily', 'Salario por día')],
        ondelete={'daily': 'set default'}  # Evita errores al desinstalar el módulo
    )

class HrContract(models.Model):
    _inherit = 'hr.contract'

    """EN LA VERSION 16 Y 17 YA CUENTA CON ESTA OPCION EN EL CONTRATO, ASI QUE NO UTILIZAR LA MISMA LOGICA EN ESAS VERSIONES EN LO QUE RESPECTA asis_marc, en las versiones mensionadas el campo es work_entry_source"""
    asis_marc = fields.Boolean(string="Asistencia por Marcación")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(models.Model, self).fields_view_get(view_id, view_type, toolbar, submenu)
        return res

    # Campo para el salario diario
    daily_wage = fields.Monetary(
        string='Jornal diario',
        default=0,
        required=False,
        tracking=True,
        help="Salario diario del empleado, se usa para los jornaleros."
    )

    # Campo relacionado con structure_type_id para poder usarlo en attrs
    wage_type = fields.Selection(
        related='structure_type_id.wage_type',
        store=True,
        readonly=True
    )
