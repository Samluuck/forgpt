from odoo import models, fields, api, _

class Banco(models.Model):
    _name = 'despacho.banco'
    _description = 'Banco'
    _order = 'name asc'

    name = fields.Char('Nombre', required=True)

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]

class CuentaBanco(models.Model):
    _name = 'despacho.cuentabanco'
    _description = 'Cuenta Bancaria'
    _order = 'banco, numero asc'

    banco = fields.Many2one(
        'despacho.banco',
        'Banco',
        required=True,
        ondelete='cascade'
    )
    numero = fields.Char(
        'Número de Cuenta',
        required=True,
        help="Número de cuenta bancaria"
    )
    titular = fields.Char(
        'Titular',
        required=True,
        help="Nombre del titular de la cuenta"
    )
    ci = fields.Char(
        'CI/RUC',
        help="Cédula de identidad o RUC del titular"
    )

    _sql_constraints = [
        ('cuenta_unique', 'unique(banco, numero)', 'Esta cuenta bancaria ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.banco.name} - {rec.numero} ({rec.titular})")
                for rec in self]

class Adelanto(models.Model):
    _name = 'despacho.adelanto'
    _description = 'Adelanto de Gastos'
    _order = 'fecha desc, id desc'

    despacho = fields.Many2one(
        'despacho.despacho',
        'Orden de Trabajo',
        required=True,
        ondelete='cascade'
    )
    empleado = fields.Many2one(
        'hr.employee',
        'Operativo',
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    monto = fields.Float(
        'Monto',
        required=True,
        digits='Account'
    )
    fecha = fields.Date(
        'Fecha',
        required=True,
        default=fields.Date.context_today
    )
    comprobante = fields.Binary(
        'Comprobante',
        attachment=True,
        help="Comprobante de transferencia del adelanto"
    )
    cuenta = fields.Many2one(
        'despacho.cuentabanco',
        'Cuenta Bancaria',
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
    ],
    string="Estado",
    readonly=True,
    tracking=True,
    group_expand='_expand_states',
    default='pendiente')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_confirm(self):
        for rec in self:
            if rec.state == 'pendiente':
                rec.state = 'aprobado'

class OrdenPago(models.Model):
    _name = 'despacho.ordenpago'
    _description = 'Orden de Pago'
    _order = 'fecha desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Orden de Pago",
        readonly=True,
        required=True,
        copy=False,
        index=True,
        default=lambda self: _('New')
    )
    despacho = fields.Many2one(
        'despacho.despacho',
        'Orden de Trabajo',
        tracking=True
    )
    empleado = fields.Many2one(
        'hr.employee',
        'Operativo',
        domain="[('company_id', '=', company_id)]",
        tracking=True
    )
    monto = fields.Float(
        'Monto',
        required=True,
        digits='Account',
        tracking=True
    )
    fecha = fields.Date(
        'Fecha',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    vencimiento = fields.Date(
        'Vencimiento',
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
    ],
    string="Estado",
    readonly=True,
    tracking=True,
    group_expand='_expand_states',
    default='pendiente')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('despacho.ordenpago.sequence') or _('New')
        return super().create(vals)

class Pago(models.Model):
    _name = 'despacho.pago'
    _description = 'Pago'
    _order = 'fecha desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="Pago",
        readonly=True,
        required=True,
        copy=False,
        index=True,
        default=lambda self: _('New')
    )
    monto = fields.Float(
        'Monto',
        required=True,
        digits='Account',
        tracking=True
    )
    fecha = fields.Date(
        'Fecha',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    comprobante = fields.Binary(
        'Comprobante',
        attachment=True,
        help="Comprobante de transferencia del pago",
        tracking=True
    )
    cuenta = fields.Many2one(
        'despacho.cuentabanco',
        'Cuenta Bancaria',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    op = fields.Many2many(
        'despacho.ordenpago',
        relation='despacho_administracion_ordenpago_pago',
        column1='pago_id',
        column2='orden_pago_id',
        string='Órdenes de Pago',
        tracking=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('despacho.pago.sequence') or _('New')
        return super().create(vals)

class HrExpenseInherit(models.Model):
    _inherit = "hr.expense"

    despacho = fields.Many2one(
        'despacho.despacho',
        'Orden de Trabajo',
        tracking=True
    )
    vencimiento = fields.Date(
        'Vencimiento',
        tracking=True
    )

    payment_mode = fields.Selection(
        selection_add=[('client_account', "Cliente")],
        ondelete={'client_account': 'set default'}
    )