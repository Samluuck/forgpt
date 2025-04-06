from datetime import timedelta
from odoo import models, fields, _, api

GENDER_SELECTION = [('male', 'Male'),
                    ('female', 'Female'),
                    ('other', 'Other')]


class HrEmployeeFamilyInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.family'
    _description = 'HR Employee Family'

    employee_id = fields.Many2one('hr.employee', string="Empleado",
                                  help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relación",
                                  help="Relationship with the employee")
    member_name = fields.Char(string='Nombre')
    member_contact = fields.Char(string='Número de contacto')
    birth_date = fields.Date(string="DOB", tracking=True)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def mail_reminder(self):
        """Sending expiry date notification for ID and Passport"""

        current_date = fields.Date.context_today(self) + timedelta(days=1)
        employee_ids = self.search(['|', ('id_expiry_date', '!=', False),
                                    ('passport_expiry_date', '!=', False)])
        for emp in employee_ids:
            if emp.id_expiry_date:
                exp_date = fields.Date.from_string(
                    emp.id_expiry_date) - timedelta(days=14)
                if current_date >= exp_date:
                    mail_content = "  Hello  " + emp.name + ",<br>Your ID " + emp.identification_id + "is going to expire on " + \
                                   str(emp.id_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('ID-%s Expired On %s') % (
                            emp.identification_id, emp.id_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': emp.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
            if emp.passport_expiry_date:
                exp_date = fields.Date.from_string(
                    emp.passport_expiry_date) - timedelta(days=180)
                if current_date >= exp_date:
                    mail_content = "  Hello  " + emp.name + ",<br>Your Passport " + emp.passport_id + "is going to expire on " + \
                                   str(emp.passport_expiry_date) + ". Please renew it before expire"
                    main_content = {
                        'subject': _('Passport-%s Expired On %s') % (
                            emp.passport_id, emp.passport_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': emp.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

    personal_mobile = fields.Char(
        string='Móvil',
        related='address_home_id.mobile', store=True,
        help="Número de móvil personal del empleado.")
    joining_date = fields.Date(
        string='Dia de ingreso',
        help="Fecha de incorporación del empleado computada a partir de la fecha de inicio del contrato",
        compute='_compute_joining_date', store=True)
    id_expiry_date = fields.Date(
        string='Fecha de caducidad',
        help='Fecha de caducidad del DNI')
    passport_expiry_date = fields.Date(
        string='Fecha de caducidad',
        help='Fecha de caducidad de la identificación del pasaporte')
    id_attachment_id = fields.Many2many(
        'ir.attachment', 'id_attachment_rel',
        'id_ref', 'attach_ref',
        string="Adjunto",
        help='Puedes adjuntar la copia de tu DNI')
    passport_attachment_id = fields.Many2many(
        'ir.attachment',
        'passport_attachment_rel',
        'passport_ref', 'attach_ref1',
        string="Adjunto",
        help='Puede adjuntar la copia del Pasaporte')
    fam_ids = fields.One2many(
        'hr.employee.family', 'employee_id',
        string='Familia', help='Información familiar')

    @api.depends('contract_id')
    def _compute_joining_date(self):
        for rec in self:
            rec.joining_date = min(rec.contract_id.mapped('date_start'))\
                if rec.contract_id else False

    @api.onchange('spouse_complete_name', 'spouse_birthdate')
    def onchange_spouse(self):
        relation = self.env.ref('hr_employee_updation.employee_relationship')
        if self.spouse_complete_name and self.spouse_birthdate:
            self.fam_ids = [(0, 0, {
                'member_name': self.spouse_complete_name,
                'relation_id': relation.id,
                'birth_date': self.spouse_birthdate,
            })]


class EmployeeRelationInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.relation'

    name = fields.Char(string="Relación",
                       help="Relación con el empleado")
