# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from dateutil.parser import parse
from odoo.exceptions import ValidationError
import time
import logging
import pytz

_logger = logging.getLogger(__name__)


class HrEmployeeInh(models.AbstractModel):
    _inherit = "hr.employee.base"

    numero_hijos = fields.Integer("Número de Hijos", compute='get_cantidadHijos')
    categoria_de_ips = fields.Selection(selection=[('e', 'Empleado/Mensualero'), ('o', 'Obrero/Destajo')], default='e')
    numero_de_asegurado = fields.Integer("Número de Asegurado de IPS")
    no_marca = fields.Boolean(string='No marca',required=False)
    cedulas_id = fields.One2many("hr.cedula",'identidad_id', string="Cedula Identidad: ")
    contrato_confidencial_id = fields.One2many("hr.confidencial",'confidencial_id', string="Contrato Confidencial: ")
    reglamiento_interno = fields.One2many("hr.reglamento", 'interno_id',string="Reglamiento Interno: ")
    ips_id= fields.One2many("hr.ips",'ips_id' ,string="Inscripción a Instituto de previsión social : ")
    ministerio_trabajo_id = fields.One2many("hr.ministerio", 'trabajo_id',string="Inscripción a Ministerio de trabajo :")
    contrato_trabajo_id = fields.One2many("hr.contratotrabajo", 'contrato_trabajo_id',string="Contrato de Trabajo :")
    antecedente_policial_id = fields.One2many("hr.antecedentepolicial","policial_id", string="Antecedente Policial: ")
    grupo_familiar_id = fields.One2many('hr.grupo_familiar', 'grupo_familiar_ids', string='Grupo Familiar:')
    curriculums_id = fields.One2many("hr.cv",'curriculum_id', string="Curriculum Vitae: ")
    antecedente_judicial_id = fields.One2many("hr.antecedentejudicial","judicial_id", string="Antecedente Judicial: ")
    titulos_id = fields.One2many("hr.titulo",'titulo_id', string="Estudios")
    @api.constrains('grupo_familiar_id')
    def get_cantidadHijos(self):
        contador_hijos = 0
        for rec in self:
            for gf in rec.grupo_familiar_id:
                print(gf.vive)
                print(gf.discapacitado)
                print(gf.relacion_parentesco)
                print(gf.papeles)
                print(gf.relacion_parentesco)
                if (gf.edad < 18 and gf.relacion_parentesco == 'hijo' and gf.papeles == True) or (gf.discapacitado == 'si' and gf.relacion_parentesco == 'hijo' and gf.papeles == True):
                    print("################## SUMA UN HIJO ########################")
                    contador_hijos += 1

            rec.numero_hijos = contador_hijos

    def alerts(self):
        # raise ValidationError('hola')
        empleados = self.env['hr.employee'].search([])
        fecha_actual = fields.Datetime.now().date()
        grupo = list()
        for e in empleados:
            if e.contract_id.trial_date_end:
                trial_date = e.contract_id.trial_date_end
                _logger.warning('trial %s' % trial_date)
                dif = (fecha_actual - trial_date).days
                _logger.warning('dif %s' % dif)
                if dif <= 2 or dif >= 0:
                    grupo.append(e)
        lista_enviar = []
        em_dep = self.env['hr.employee'].search([('department_id', '=', 40)])
        lista_enviar = em_dep.mapped('user_id')
        _logger.warning('asaniu %s' % grupo)
        for g in grupo:
            aa = self.sudo().message_notify(email_from='odoo@trafosur.com.py',
                                         partner_ids=lista_enviar.mapped('partner_id').ids,
                                         subject="Alerta de Vencimiento de periodo de Prueba",
                                         body=('El periodo de prueba del empleado %s con CI %s vence en %s días') % (
                                         g.name, dif, g.identification_id))
            _logger.warning('c %s' % aa)


        lista_enviar = []

