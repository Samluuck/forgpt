from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
import time
from datetime import time as datetime_time
from dateutil.relativedelta import relativedelta
import calendar
import logging
from datetime import date, datetime, time,timedelta
import babel
from odoo import fields, models, exceptions, api , _

import pytz

_logger = logging.getLogger(__name__)



class hr_payslip_inh(models.Model):
    _inherit = "hr.payslip"

    dias_pagados = fields.Integer(compute="dias_habiles")


    @api.depends('employee_id', 'date_from', 'date_to')
    def dias_habiles(self):
            for rec in self:
                print('########################### INGRESA A LA FUNCION DE DIAS HABILESS    #########################3')
                c=0
                if rec.employee_id:
                    for emp in rec.employee_id:
                            print("[-----------------------> EMPLEADOS <------------------ %s", emp.name)
                            if rec.employee_id.contract_id.date_start >= rec.date_from:
                                print("++++++++++++++++++ Entra en la condicion si la fecha de contrato es mayor o igual ++++++++++++++++++")
                                c = 30 + (rec.date_from.day - rec.employee_id.contract_id.date_start.day)
                                rec.dias_pagados = c
                            else:

                                print("___________________ Entra en la condicion si la fecha de contrato es menor _______________")
                                c=1
                                    # rec.date_from = rec.date_from + timedelta(days=1)
                                rec.dias_pagados = c
                else:
                    rec.dias_pagados = c

