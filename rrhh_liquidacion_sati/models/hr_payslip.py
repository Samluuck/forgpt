from odoo import models, fields, api, exceptions, _
from dateutil.relativedelta import relativedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    antiguedad = fields.Integer(string="Antigüedad (Años)", compute='_compute_employee_seniority', store=True, help="Campo de la antiguedad en años del empleado")
    preaviso_correspondido = fields.Integer(compute='_compute_preaviso_correspondido', string='Días de Preaviso Correspondidos')
    salario_mes_1 = fields.Float(string="Salario mes 1", store=True)
    salario_mes_2 = fields.Float(string="Salario mes 2", store=True)
    salario_mes_3 = fields.Float(string="Salario mes 3", store=True)
    salario_mes_4 = fields.Float(string="Salario mes 4", store=True)
    salario_mes_5 = fields.Float(string="Salario mes 5", store=True)
    salario_mes_6 = fields.Float(string="Salario mes 6", store=True)
    salario_promedio_ultimos_meses = fields.Float(compute='calculate_previous_six_months_salaries', store=True, string="Salario Promedio Últimos 6 Meses")
    indemnizacion = fields.Float(compute='_compute_indemnizacion', string="Indemnización por Despido Injustificado ", store=True)
    dias_trabajados = fields.Integer(string="Días pagados en liquidación", compute="_compute_dias_trabajados")
    motivo_despido = fields.Char(string="Motivo de la desvinculación")


    @api.depends('employee_id', 'contract_id.date_start')
    def _compute_employee_seniority(self):
        """
        Calcula la antigüedad del empleado basada en la fecha de inicio del contrato.
        Esta función se actualiza cada vez que se crea una nómina, asegurando que la antigüedad esté siempre actualizada.
        """
        for record in self:
            if record.employee_id and record.contract_id and record.contract_id.date_start:
                # Obtener la fecha de inicio desde el contrato
                start_date = record.contract_id.date_start
                # Calcula la diferencia de años hasta la fecha actual
                today = fields.Date.today()
                difference = relativedelta(today, start_date)
                record.antiguedad = difference.years
            else:
                # Si no hay fecha de inicio en el contrato, establece la antigüedad en 0
                record.antiguedad = 0

    @api.depends('antiguedad')
    def _compute_preaviso_correspondido(self):
        """
        Calcula los días de preaviso correspondidos basados en la antigüedad del empleado.
        El cálculo se basa en una regla ficticia donde cada año de antigüedad aumenta los días de preaviso en 2, hasta un máximo de 30 días.
        """
        for record in self:
            if record.antiguedad:
                # Calcula los días de preaviso como dos días por año de antigüedad
                record.preaviso_correspondido = min(2 * record.antiguedad, 30)
            else:
                record.preaviso_correspondido = 0

    @api.depends('date_from')
    def calculate_previous_six_months_salaries(self):
        # Iterar sobre cada registro (nómina) para calcular los salarios de los últimos 6 meses
        for record in self:
            # Inicializar la fecha de fin para empezar el cálculo desde el mes anterior a la fecha de inicio de la nómina actual
            end_date = record.date_from
            salaries = []  # Lista para almacenar los salarios de cada uno de los últimos 6 meses
            # Calcular los salarios de los últimos 6 meses
            for i in range(6):
                # Calcular la fecha de inicio del mes anterior
                start_date = end_date - relativedelta(months=1)
                # Buscar las nóminas del empleado que caigan dentro del mes calculado
                payslips = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date_from', '>=', start_date),
                    ('date_to', '<', end_date),
                    ('line_ids.salary_rule_id.salario_neto', '=', True),
                    # Filtrar solo las líneas de nómina marcadas como 'salario_neto'
                ])

                # Calcular el salario total para el mes, sumando los montos de las líneas relevantes de todas las nóminas encontradas
                total_salario = sum(line.amount for payslip in payslips for line in payslip.line_ids if
                                    line.salary_rule_id.salario_neto)
                salaries.append(total_salario)
                # Actualizar la fecha de fin para el siguiente mes hacia atrás
                end_date = start_date

            # Asignar los salarios calculados a los campos correspondientes en el registro de nómina
            # Se asigna de manera inversa porque el último salario calculado corresponde al mes más reciente
            record.salario_mes_1 = salaries[5] if len(salaries) > 5 else 0
            record.salario_mes_2 = salaries[4] if len(salaries) > 4 else 0
            record.salario_mes_3 = salaries[3] if len(salaries) > 3 else 0
            record.salario_mes_4 = salaries[2] if len(salaries) > 2 else 0
            record.salario_mes_5 = salaries[1] if len(salaries) > 1 else 0
            record.salario_mes_6 = salaries[0] if len(salaries) > 0 else 0

            # Calcular el salario promedio dividiendo por 6 sin importar si algunos meses tienen salario de 0
            record.salario_promedio_ultimos_meses = sum(salaries) / 6

    @api.depends('salario_mes_1', 'salario_mes_2', 'salario_mes_3', 'salario_mes_4', 'salario_mes_5', 'salario_mes_6',
                 'antiguedad')
    def _compute_indemnizacion(self):
        for record in self:
            # Calcula el salario promedio de los últimos 6 meses
            salario_promedio = (record.salario_mes_1 + record.salario_mes_2 +
                                record.salario_mes_3 + record.salario_mes_4 +
                                record.salario_mes_5 + record.salario_mes_6) / 6
            # Calcula el salario diario
            salario_diario = salario_promedio / 30  # Asumiendo 30 días al mes
            print("Salario promedio",salario_diario)
            # Calcula los jornales diarios
            jornales_diarios = 15 * record.antiguedad  # 15 días por cada año de servicio

            # Calcula la indemnización total
            record.indemnizacion = salario_diario * jornales_diarios
            print("Indemnizacion",record.indemnizacion)


    @api.depends('date_from', 'date_to')
    def _compute_dias_trabajados(self):
        for record in self:
            if record.date_from and record.date_to:
                # Calcular la diferencia en días
                delta = record.date_to - record.date_from
                # Asignar el número de días más uno porque ambos días cuentan
                record.dias_trabajados = delta.days + 1
            else:
                record.dias_trabajados = 0
    def compute_sheet(self):
        super(HrPayslip, self).compute_sheet()
        self.calculate_previous_six_months_salaries()
        self._compute_indemnizacion()  # Asegura que se calcule después de actualizar los salarios y otras dependencias


