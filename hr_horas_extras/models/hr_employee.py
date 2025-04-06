from odoo import fields, models, exceptions, api
import logging

_logger = logging.getLogger(__name__)



class HrEmployeeInh(models.AbstractModel):
    _inherit = "hr.employee.base"
    #REALIZAMOS LA HERENCIA DE hr.employee.base PORQUE DESDE EL ODOO 15 SE DEBE REALIZAR DE ESA MANERA PARA TAMBIEN SE CREE EN LA TABLA DE hr.employee,public
    cobra_entrada_anticipada = fields.Boolean(string='Cobra Entrada Anticipada?',help='Marca este campo en caso de que sea un colaborador que cobra entrada anticipada ', tracking=True)
    cobra_horas_extras = fields.Boolean(string='Cobra horas Extras?',help='Marca este campo en caso de que sea un colaborador que cobra hoas extras ', tracking=True)
    horario_nocturno = fields.Boolean(string='Maneja horario nocturno?',help='Marca este campo en caso de que sea un colaborador que cuenta con horas nocturnas', tracking=True)
    horario_diurno = fields.Boolean(string='Maneja horario diurno?',help='Marca este campo en caso de que sea un colaborador que cuenta con horas diurnas', tracking=True)
    llegada_tardia = fields.Boolean(string='Se debe descontar las llegadas tardias?',help='Marca este campo en caso de que sea un colaborador que cuenta con descuento de llegadas tardias ')


