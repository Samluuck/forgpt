from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from num2words import num2words

class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    last_deduction_month = fields.Char(string="Último Mes de Deducción Aplicada")
    calculocuota= fields.Float("Monto por cuota", compute="_compute_calculocuota")
    loan_amount_text = fields.Char(string="Monto en palabras", compute="_compute_loan_amount_text")
    fecha_fin_prestamo = fields.Date(string="Fecha Fin Prestamo", compute="_compute_fecha_fin_prestamo", store=True)

# Funcion Numeros a Letras

    @api.depends('loan_amount')
    def _compute_loan_amount_text(self):
        for record in self:
            if record.loan_amount:
                record.loan_amount_text = f"GUARANIES {num2words(int(record.loan_amount), lang='es').upper()}"
            else:
                record.loan_amount_text= ""

# Funcion del calculo de cuotas

    @api.depends('loan_amount', 'installment')
    def _compute_calculocuota(self):
        for record in self:
            record.calculocuota = record.loan_amount / record.installment if record.installment else 0
    @api.depends('payment_date', 'installment')

# Funcion Fecha de fin de prestamo

    def _compute_fecha_fin_prestamo(self):
        for record in self:
            if record.payment_date and record.installment:
                record.fecha_fin_prestamo = record.payment_date + relativedelta(months=record.installment)
            else:
                record.fecha_fin_prestamo = False


# Boton imprimir
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(models.Model,self).fields_view_get(view_id, view_type, toolbar, submenu)
        return res
    
    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result

    def _compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid
    print("INGRESA A  _compute_loan_amount")

    name = fields.Char(string="Nombre del Préstamo/Adelanto", default="/", readonly=True, help="Nombre del Préstamo/Adelanto")
    date = fields.Date(string="Fecha", default=fields.Date.today(), help="Fecha",tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True, help="Employee",tracking=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Departamento", help="Empleado")
    installment = fields.Integer(string="N° de cuotas", default=1, help="Número de Cuotas",tracking=True)
    payment_date = fields.Date(string="Fecha de inicio del pago", required=True, default=fields.Date.today(), help="Fecha de "
                                                                                                             "el "
                                                                                                             "pago")
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Línea de préstamo", index=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, help="Moneda",
                                  default=lambda self: self.env.user.company_id.currency_id)
    loan_amount = fields.Float(string="Monto del préstamo/adelanto", required=True, help="Monto del préstamo/adelanto")
    total_amount = fields.Float(string="Cantidad total", store=True, readonly=True, compute='_compute_loan_amount',
                                help="Monto total del préstamo")
    balance_amount = fields.Float(string="Balance de Cuenta", store=True, compute='_compute_loan_amount', help="Balance de Cuenta")
    total_paid_amount = fields.Float(string="Monto total pagado", store=True, compute='action_payslip_done',
                                     help="Monto total pagado")
    print("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-",total_paid_amount)

    tipo_descuento = fields.Many2one("lista.descuentos",tracking=True)
    loan_deduction_code = fields.Char(string='Código de deducción',
                                      help="Código de la deducción del préstamo o adelanto")

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('waiting_approval_1', 'Enviado'),
        ('approve', 'Aprobado'),
        ('refuse', 'Rechazado'),
            ('cancel', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True, copy=False, )

    @api.model
    def create(self, values):
        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
             ('balance_amount', '!=', 0)])

        values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
        res = super(HrLoan, self).create(values)
        return res

    def compute_installment(self):
        print("Ingresa a compute_installment ")
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            loan._compute_loan_amount()
        return True

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_submit(self):
        self.write({'state': 'waiting_approval_1'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Por favor calcule la cuota"))
            else:
                self.write({'state': 'approve'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete a loan which is not in draft or cancelled state')
        return super(HrLoan, self).unlink()


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Fecha de pago", required=True, help="Fecha del pago")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Empleado")
    amount = fields.Float(string="Cantidad", required=True, help="Cantidad")
    paid = fields.Boolean(string="Pagado", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Ref. de préstamo.", help="Préstamo")
    payslip_id = fields.Many2one('hr.payslip', string="Nómina Ref.", help="Payslip")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_loans(self):
        print("Ingresa a _compute_employee_loans")
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')