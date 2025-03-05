from odoo import models, api, fields, Command
from odoo.exceptions import ValidationError


class PayslipOverTime(models.Model):
    _inherit = 'hr.payslip'

    overtime_ids = fields.Many2many('hr.overtime', string="Overtime Requests")

    # @api.model
    # def _compute_input_line_ids(self):
    #     """
    #     Escribe las horas extras en las líneas de entrada de la nómina.
    #     """
    #     print(">>> Método _compute_input_line_ids llamado para Payslip:", self.id)
    #     res = super(PayslipOverTime, self)._compute_input_line_ids()
    #
    #     # Referencias a los registros relacionados con horas extras
    #     overtime_type = self.env.ref('ent_ohrms_overtime.hr_salary_rule_overtime', raise_if_not_found=False)
    #     overtime_input_type = self.env.ref('ent_ohrms_overtime.input_overtime_payroll', raise_if_not_found=False)
    #
    #     if not overtime_type or not overtime_input_type:
    #         print(">>> Referencias de horas extras no encontradas: overtime_type or overtime_input_type is None")
    #         return res
    #
    #     # Buscar las horas extras relacionadas con el empleado y contrato dentro del período de la nómina
    #     overtime_id = self.env['hr.overtime'].search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('contract_id', '=', self.contract_id.id),
    #         ('state', '=', 'approved'),
    #         ('payslip_paid', '=', False),
    #         ('date_from', '>=', self.date_from),
    #         ('date_to', '<=', self.date_to)
    #     ])
    #     print(">>> Horas extras encontradas:", overtime_id)
    #
    #     if overtime_id and self.struct_id and overtime_input_type in self.struct_id.input_line_type_ids:
    #         # Calcular el monto total de horas extras
    #         cash_amount = sum(overtime_id.mapped('cash_hrs_amount')) + sum(overtime_id.mapped('cash_day_amount'))
    #         print(">>> Monto calculado para horas extras:", cash_amount)
    #
    #         # Crear nueva línea de entrada
    #         input_data = [
    #             Command.create({
    #                 'name': overtime_type.name,
    #                 'amount': cash_amount,
    #                 'input_type_id': overtime_input_type.id
    #             })
    #         ]
    #         print(">>> Datos de entrada generados:", input_data)
    #
    #         # Actualizar las líneas de entrada eliminando duplicados
    #         self.input_line_ids = [(5, 0, 0)] + input_data
    #         print(">>> Líneas de entrada actualizadas en input_line_ids:", self.input_line_ids)
    #
    #     return res

    def get_payslip_inputs(self):
        for rec in self:
            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue

            lista_diccionario = []

            # Manejo de horas extras
            overtime_input_type = self.env.ref('hr_overtime.input_overtime_payroll', raise_if_not_found=False)
            if not overtime_input_type:
                raise ValidationError("El tipo de entrada para horas extras no está configurado.")

            overtime_records = self.env['hr.overtime'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('contract_id', '=', rec.contract_id.id),
                ('state', '=', 'approved'),
                ('payslip_paid', '=', False),
                ('date_from', '>=', rec.date_from),
                ('date_to', '<=', rec.date_to)
            ])

            # Verifica que overtime_records realmente contiene registros
            print(f">>> overtime_records encontrados: {overtime_records}")

            for overtime in overtime_records:
                # Crear datos para la entrada de horas extras
                data = {
                    'name': overtime.name,
                    'code': overtime_input_type.code,
                    'amount': overtime.cash_hrs_amount + overtime.cash_day_amount,
                    'sequence': 10,
                    'input_type_id': overtime_input_type.id,
                    'contract_id': rec.contract_id.id,
                    'payslip_id': rec.id,
                }
                lista_diccionario.append(data)

            # Crear y asignar las entradas en input_line_ids
            entrada = self.env['hr.payslip.input'].browse([])
            for r in lista_diccionario:
                entrada += entrada.new(r)
            rec.input_line_ids = entrada

            # # Marcar horas extras como pagadas
            # overtime_records.write({'payslip_paid': True})

    def compute_sheet(self):
        for rec in self:
            rec.get_payslip_inputs()
            super(PayslipOverTime, rec).compute_sheet()

    def action_payslip_done(self):
        """
        Marca las solicitudes de horas extras como pagadas solo si la nómina está en estado 'done'.
        """
        print(">>> Método action_payslip_done llamado para Payslip:", self.id)

        # Verificar el estado de la nómina
        print(f">>> Estado de la nómina: {self.state}")
        estado = ''
        if self.state == 'verify':
            estado = 'done'
        else:
            estado = self.state
        # Verificar si la nómina está en estado 'done'
        if estado == 'done':
            # Realizar la búsqueda de horas extras no pagadas asociadas a la nómina
            overtime_records = self.env['hr.overtime'].search([
                ('employee_id', '=', self.employee_id.id),
                ('contract_id', '=', self.contract_id.id),
                ('state', '=', 'approved'),
                ('payslip_paid', '=', False),
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to)
            ])

            # Marcar las horas extras como pagadas
            for recd in overtime_records:
                recd.write({'payslip_paid': True})
                print(f">>> Solicitud de horas extras {recd.id} marcada como pagada.")
        else:
            print(">>> La nómina no está en estado 'done', no se marcarán las horas extras como pagadas.")

        return super(PayslipOverTime, self).action_payslip_done()

