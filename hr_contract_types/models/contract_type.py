from num2words import num2words
from odoo import api, fields, models, _
from datetime import datetime

class ContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Tipo de Contrato'
    _order = 'sequence, id'

    name = fields.Char(string='Contract Type', required=True, help="Nombre")
    es_mensualero = fields.Boolean(string="Mensualero",
                                   help="Marcar si es mensualero para el reporte de resumen general de personas")
    es_jornalero = fields.Boolean(string="Jornalero",
                                  help="Marcar si es jornalero para el reporte de resumen general de personas")
    contrato_indefinido = fields.Boolean(string="Contrato Indefinido", help="Marcar si es Contrato Indefinido")
    contrato_determinado = fields.Boolean(string="Contrato Por Tiempo Determinado",
                                          help="Marcar si es Contrato Determinado")
    es_adenda = fields.Boolean(string="Es adenda?", help="Marcar si es adenda")
    sequence = fields.Integer(help="Da la secuencia al mostrar una lista de Contrato.", default=10)
    contract_id = fields.Many2one('hr.contract', string="Contrato Relacionado")
    employee_id = fields.Many2one('hr.employee', string="Empleado")

    # Campos HTML
    contrato_indef = fields.Html()
    contrato_det = fields.Html()
    es_adenda_ht = fields.Html()

    meses = {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abril',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre'
    }


class ContractInherit(models.Model):
    _inherit = 'hr.contract'

    contract_type_id = fields.Many2one('hr.contract.type', string="Tipo de Contrato",
                              required=True, help="Tipo de contrato del empleado",
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1))
    es_adenda_check = fields.Boolean(string="Es adenda?", help="Marcar si es adenda")
    fecha_noti_adenda = fields.Date(string="Fecha de notificacion de Adenda", help="Fecha de notificacion de Adenda")
    fecha_inicio_adenda = fields.Date(string="Fecha de inicio de Adenda", help="Fecha de inicio de Adenda")

    formatted_contract = fields.Html()
    meses = {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abril',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre'
    }

    def reemplazar_campos(self, tipo_contrato):
        dia = datetime.now().day
        mes = datetime.now().month
        anio = datetime.now().year

        texto = f'{dia} días del mes de {self.meses[mes]} del {anio}'
        if tipo_contrato == 1:
            contrato_anterior = self.contract_type_id.contrato_indef or ''
        elif tipo_contrato == 2:
            contrato_anterior = self.contract_type_id.contrato_det or ''
        elif tipo_contrato == 3:
            contrato_anterior = self.contract_type_id.es_adenda_ht or ''

        # Diccionario para valores de estado marital
        MARITAL_TRANSLATIONS = {
            'single': 'Soltero(a)',
            'married': 'Casado(a)',
            'cohabitant': 'Cohabitante legal',
            'widower': 'Viudo(a)',
            'divorced': 'Divorciado(a)'
        }

        # Obtener el valor traducido del estado marital
        marital_es = MARITAL_TRANSLATIONS.get(self.employee_id.marital, ' ')

        #Fecha actual en tiempo real
        contrato_anterior = contrato_anterior.replace('FECHA_DE_HOY', texto)

        # Reemplazo condicionado para EMPLEADO_NAME
        if self.employee_id.name:
            contrato_anterior = contrato_anterior.replace('EMPLEADO_NAME', self.employee_id.name.upper())
        else:
            contrato_anterior = contrato_anterior.replace('EMPLEADO_NAME', 'Nombre de empleado no ingresado.')

        # Reemplazo condicionado para EMPLEADO_CI
        if self.employee_id.identification_id:
            contrato_anterior = contrato_anterior.replace('EMPLEADO_CI', self.employee_id.identification_id)
        else:
            contrato_anterior = contrato_anterior.replace('EMPLEADO_CI', 'CI no ingresada.')

        # Reemplazo condicionado para MARITAL
        if marital_es:
            contrato_anterior = contrato_anterior.replace('MARITAL', marital_es)
        else:
            contrato_anterior = contrato_anterior.replace('MARITAL', 'No se ha seleccionado un estado civil')

        # Reemplazo condicionado para CIUDAD
        if self.employee_id.address_home_id.city:
            contrato_anterior = contrato_anterior.replace('CIUDAD', self.employee_id.address_home_id.city)
        else:
            contrato_anterior = contrato_anterior.replace('CIUDAD', 'La ciudad del empleado se encuentra vacia')

        # Reemplazo condicionado para DIRECCION
        if self.employee_id.address_home_id:
            contrato_anterior = contrato_anterior.replace('DIRECCION', f"{self.employee_id.address_home_id.street or ''} {self.employee_id.address_home_id.street2 or ''}".strip())
        else:
            contrato_anterior = contrato_anterior.replace('DIRECCION', 'La direccion del empleado se encuentra vacia')

        # Reemplazo condicionado para JOB_ID
        if self.employee_id.job_id.name:
            contrato_anterior = contrato_anterior.replace('JOB_ID', str(self.employee_id.job_id.name))
        else:
            contrato_anterior = contrato_anterior.replace('JOB_ID', 'El puesto del empleado no fue asignado')

        # Verificar cuál campo usar basado en su valor
        if self.hourly_wage > 0:
            monto_a_usar = self.hourly_wage
            monto_en_letras = self.hourly_wage
        else:
            monto_a_usar = self.wage
            monto_en_letras = self.wage

        # Convertir el monto a un string y reemplazarlo

        contrato_anterior = contrato_anterior.replace('numero_monto_id', str(monto_a_usar))

        # Convertir Monto en Letras
        monto_en_letras = num2words(monto_a_usar, lang='es').upper()
        contrato_anterior = contrato_anterior.replace('MONTO_ID', monto_en_letras)

        if self.date_start:
            fecha_inicio = self.date_start.strftime('%d de %B de %Y')
            fecha_inicio_es = fecha_inicio.replace(self.date_start.strftime('%B'),
                                                             self.meses[self.date_start.month])
            contrato_anterior = contrato_anterior.replace('START_CONTRACT', fecha_inicio_es)
        else:
            contrato_anterior = contrato_anterior.replace('START_CONTRACT', 'Fecha de inicio de contrato no ingresada')

        # Reemplazo de fecha de fin solo si existe date_end
        if self.employee_id.contract_id.date_end:
            fecha_fin = self.employee_id.contract_id.date_end.strftime('%d-%m-%Y')
            contrato_anterior = contrato_anterior.replace('END_CONTRACT',
                                                          f"{fecha_fin}, llegada esta fecha este contrato individual de trabajo terminará sin responsabilidad alguna para las partes.")
        else:
            # Si no hay fecha de fin, elimina cualquier texto END_CONTRACT
            contrato_anterior = contrato_anterior.replace('END_CONTRACT', 'Fecha de finalizacion de contrato no ingresada')

        #  Fecha de notificacion de adenda
        if self.fecha_noti_adenda:
            # Convertir la fecha en formato 'Día de Mes de Año' con traducción al español
            fecha_noti_adenda = self.fecha_noti_adenda.strftime('%d de %B de %Y')
            fecha_noti_adenda = fecha_noti_adenda.replace(
                self.fecha_noti_adenda.strftime('%B'),
                self.meses[self.fecha_noti_adenda.month]
            )
            contrato_anterior = contrato_anterior.replace('FECHA_NOTI_ADENDA', fecha_noti_adenda)
        else:
            # Si no hay fecha, colocar un mensaje predeterminado
            contrato_anterior = contrato_anterior.replace('FECHA_NOTI_ADENDA', 'Fecha de notificacion de adenda no ingresada')

        self.formatted_contract = contrato_anterior

        return self.formatted_contract