# -*- coding: utf-8 -*-

from odoo import models, fields, api


class hr_company(models.Model):
    _inherit = "res.company"

    nro_patronal_ips= fields.Char(string="Nro. Patronal IPS")
    actividad_mtess= fields.Char(string="Actividades MTESS")


class hr_payroll_run_ext(models.Model):
    _inherit = "hr.payslip.run"

    def generate_txt_file(self):
        print("------------------> INGRESA A generate_txt_file <---------------------- ")
        return self.env.ref('hr_wizard_nomina.hr_payroll_run_txt_action').read()[0]
