from odoo import models, fields, api, _


class Banco(models.Model):
    _name = 'despachos.banco'
    _description = 'despachos.banco'

    name = fields.Char()


class CuentaBanco(models.Model):
    _name = 'despachos.cuentabanco'
    _description = 'despachos.cuentabanco'

    banco = fields.Many2one('despachos.banco', 'Banco')
    numero = fields.Char('CTA Nro')
    titular = fields.Char('Titular')
    ci = fields.Char('CI')

    def name_get(self):
        result = []
        for record in self:
            record_name = record.banco.name + " - " + record.numero
            result.append((record.id, record_name))
        return result


class Adelanto(models.Model):
    _name = 'despachos.adelanto'
    _description = 'despachos.adelanto'

    despacho = fields.Many2one('despachos.despacho', 'Orden de trabajo')
    empleado = fields.Many2one('hr.employee', 'Operativo')
    monto = fields.Float('Monto')
    fecha = fields.Date('Fecha')

    comprobante = fields.Binary('Comprobante de transferencia', attachment=True)
    cuenta = fields.Many2one('despachos.cuentabanco', 'Cuenta')

    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
    ], string="Estado", readonly=False, group_expand='_expand_states', default='pendiente')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_confirm(self):
        for rec in self:
            if rec.state == 'pendiente':
                rec.state = 'aprobado'


class OrdenPago(models.Model):
    _name = 'despachos.ordenpago'
    _description = 'Orden de Pago'

    name = fields.Char(
        string=_("Orden de Pago"), readonly=True, required=True, copy=False, default=lambda self: _('New'))
    despacho = fields.Many2one('despachos.despacho', 'Orden de trabajo')
    empleado = fields.Many2one('hr.employee', 'Operativo')
    monto = fields.Float('Monto')
    fecha = fields.Date('Fecha')
    vencimiento = fields.Date('Vencimiento')
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
    ], string="Estado", readonly=False, group_expand='_expand_states', default='pendiente')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('despachos.ordenpago.sequence') or _('New')
        result = super(OrdenPago, self).create(vals)
        return result


class Pago(models.Model):
    _name = 'despachos.pago'
    _description = 'despachos.pago'

    name = fields.Char(
        string=_("Pago"), readonly=True, required=True, copy=False, default=lambda self: _('New'))
    monto = fields.Float('Monto')
    fecha = fields.Date('Fecha')

    comprobante = fields.Binary('Comprobante de transferencia', attachment=True)
    cuenta = fields.Many2one('despachos.cuentabanco', 'Cuenta')

    op = fields.Many2many('despachos.ordenpago', relation='despachos_administracion_ordenpago_pago',
                          string='Ordenes de Pago')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('despachos.pago.sequence') or _('New')
        result = super(Pago, self).create(vals)
        return result


# VISTAS HEREDADAS
class HrExpenseInherit(models.Model):
    _inherit = "hr.expense"

    despacho = fields.Many2one('despachos.despacho', 'Orden de trabajo')
    vencimiento = fields.Date('Vencimiento')

    payment_mode = fields.Selection(selection_add=[
        ('client_account', "Client")
    ])
