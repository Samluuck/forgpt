from odoo import fields, models, exceptions, api
import logging
from datetime import date, datetime

_logger = logging.getLogger(__name__)



class HrEmployeeInh(models.AbstractModel):
    _inherit = "hr.employee.base"
    #REALIZAMOS LA HERENCIA DE hr.employee.base PORQUE DESDE EL ODOO 15 SE DEBE REALIZAR DE ESA MANERA PARA TAMBIEN SE CREE EN LA TABLA DE hr.employee,public
    supervisor = fields.Boolean(string='Es un supervisor Jefe?',help='Marca este campo en caso de que sea un jefe supervisor para el reporte de resumen general de personas')
    employee_age = fields.Char(string="Edad")

    @api.onchange('birthday')
    def onchange_employee_birthday(self):
        if self.birthday:
            today = date.today()
            age = today.year - self.birthday.year - (
                        (today.month, today.day) < (self.birthday.month, self.birthday.day))
            self.employee_age = str(age)

