from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    loan_deduction_amount = fields.Float(string='Monto de la deducción del préstamo o adelanto', compute='_compute_loan_deduction_amount', store=True, help="Monto a deducir por préstamo o adelanto")

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_loan_deduction_amount(self):
        _logger.info('Ingresando a _compute_loan_deduction_amount')
        for payslip in self:
            total_deduction = 0.0
            if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                payslip.loan_deduction_amount = total_deduction
                continue

            loans = self.env['hr.loan'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'approve')
            ])
            for loan in loans:
                for line in loan.loan_lines:
                    if payslip.date_from <= line.date <= payslip.date_to:
                        total_deduction += line.amount

            payslip.loan_deduction_amount = total_deduction
            _logger.info('Deducción total calculada: %s', total_deduction)

    def action_payslip_done(self):
        _logger.info('Ingresando a action_payslip_done')
        for slip in self:
            loans = self.env['hr.loan'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', '=', 'approve')
            ])
            for loan in loans:
                total_paid_amount = loan.total_paid_amount
                for line in loan.loan_lines:
                    if slip.date_from <= line.date <= slip.date_to:
                        line.paid = True
                        total_paid_amount += line.amount
                        _logger.info('Línea de préstamo pagada: Loan ID %s, Line ID %s, Monto pagado: %s', loan.id, line.id, line.amount)

                # Actualizar el campo total_paid_amount en el préstamo
                loan.total_paid_amount = total_paid_amount
                _logger.info('Total pagado actualizado para el préstamo: Loan ID %s, Total Pagado: %s', loan.id, loan.total_paid_amount)

        return super(HrPayslip, self).action_payslip_done()

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_payslip_inputs_amount(self):
        _logger.info('Ingresando a get_payslip_inputs_amount')
        for rec in self:
            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue

            loans = self.env['hr.loan'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approve')
            ])

            for loan in loans:
                loan_deduction = 0.0
                input_type = self.env['hr.payslip.input.type'].search(
                    [('code', '=', loan.tipo_descuento.codigo)],
                    limit=1
                )

                existing_input = self.env['hr.payslip.input'].search([
                    ('payslip_id', '=', rec.id),
                    ('input_type_id', '=', input_type.id)
                ], limit=1)

                for line in loan.loan_lines:
                    if rec.date_from <= line.date <= rec.date_to:
                        loan_deduction += line.amount

                if loan_deduction > 0:
                    if not input_type:
                        _logger.warning('No se encontró el tipo de entrada para el préstamo: Loan ID %s', loan.id)
                        continue

                    if existing_input:
                        existing_input.amount += loan_deduction
                        _logger.info('Entrada de nómina actualizada con el monto de deducción: %s', existing_input)
                    else:
                        input_data = {
                            'name': input_type.name,
                            'payslip_id': rec.id,
                            'sequence': 10,
                            'amount': loan_deduction,
                            'input_type_id': input_type.id,
                        }
                        self.env['hr.payslip.input'].create(input_data)
                        _logger.info('Entrada de nómina creada: %s', input_data)

    def compute_sheet(self):
        _logger.info('INGRESA A compute_sheet')

        for rec in self:
            rec.get_payslip_inputs_amount()
            super(HrPayslip, rec).compute_sheet()
