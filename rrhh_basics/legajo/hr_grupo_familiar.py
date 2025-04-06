
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, datetime, time
#from dateutil.parser import parse obsoleto para python 3 en adelante
from dateutil.relativedelta import relativedelta

class hr_grupo_familiar(models.Model):
    _name="hr.grupo_familiar"

    nombre_apellido=fields.Char(string="Nombre y Apellido", required=True,tracking=True)
    ci=fields.Char(string="Cédula",tracking=True)
    fecha_nacimiento=fields.Date(string="Fecha de Nacimiento", default=fields.Date.today,tracking=True)
    relacion_parentesco=fields.Selection(selection=[
                                    ('hijo','Hijo/a'), ('conyuge', 'Conyuge'),('concubino', 'Concubino/a'),
                                     ('nieto', 'Nieto/a'), ('padre', 'Padre'), ('madre', 'Madre'),
                                     ('hermano/a','Hermano/a'),('bajo_tutela_legal','Bajo Tutela Legal'),
                                     ('abuelo/a','Abuelo/a'),('otro','Otro')
                                                    ],string="Relación Parentesco", required=True,tracking=True)
    seguro_medico = fields.Selection(selection=[('si','Si'),('no','No')],string="Seguro Médico")
    vive=fields.Selection(selection=[('si','Si'),('no','No')])
    discapacitado=fields.Selection(selection=[('si','Si'),('no','No')],tracking=True)
    # documentos_ids=fields.One2many('hr.grupo_familiar_documento','documento_id')
    grupo_familiar_ids=fields.Many2one('hr.employee',
                                      ondelete='cascade', string="Empleado",readonly=True)
    edad = fields.Integer('Edad' , compute='get_edad' , store=True)
    seguro_odontologico = fields.Selection(selection=[('si','Si'),('no','No')],string="Seguro Odontológico")
    telefono = fields.Char('Teléfono')
    celular = fields.Char('Celular')
    papeles= fields.Boolean("Presentó papeles",tracking=True)
    adjunto_papales = fields.Binary(string="Papeles", tracking=True)
    @api.depends('fecha_nacimiento')
    def get_edad(self):
        for rec in self:
            if rec.fecha_nacimiento:
                fecha_nacimiento_empleado = rec.fecha_nacimiento
                fecha_letra = str(fecha_nacimiento_empleado)
                fecha = datetime.strptime(fecha_letra, '%Y-%m-%d')
                print(type(fecha))
                fecha_actual = datetime.now()
                print(fecha_actual)
                print(fecha)
                fecha_nacimiento = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0)
                diferencia = (fecha_actual - fecha_nacimiento)
                redondeo = round(diferencia.days / 365)
                print(diferencia.days / 365)
                print(redondeo)
                print(type(datetime.now()))
                print(type(rec.fecha_nacimiento))
                edad = relativedelta(datetime.now(), fecha)
                print(f"{edad.years} años, {edad.months} meses y {edad.days} días")
                rec.edad = edad.years