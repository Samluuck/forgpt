# -*- coding: utf-8 -*-

from odoo import models, fields, api



class hr_company(models.Model):
    _inherit = "res.company"

    nro_cuenta= fields.Char(string="Nro Cuenta Continental")


class hr_payroll_run_ext(models.Model):
    _inherit = "hr.payslip.run"

    def generar_archivo_banco(self):
        print("------------------> INGRESA A generate_txt_file <---------------------- ")
        return self.env.ref('rrhh_payroll_bancos_continental.hr_payroll_run_txt_action').read()[0]