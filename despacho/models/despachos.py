from odoo import models, fields, api, _
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import base64
import logging

_logger = logging.getLogger(__name__)


class Contenedor(models.Model):
    _name = 'despacho.contenedor'
    _description = 'Contenedor de Despacho'

    tipo = fields.Many2one('despacho.tipo_contenedor', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    despacho = fields.Many2one('despacho.despacho', 'Despacho')

    def name_get(self):
        return [(record.id, record.numero) for record in self]


class Mercaderia(models.Model):
    _name = 'despacho.mercaderia'
    _description = 'Mercadería'
    name = fields.Char('Descripción')


class UnidadMedida(models.Model):
    _name = 'despacho.unidad_medida'
    _description = 'Unidad de Medida'
    name = fields.Char('Descripción')


class Barcaza(models.Model):
    _name = 'despacho.barcaza'
    _description = 'Barcaza'
    name = fields.Char('Descripción')


class Despacho(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'despacho.despacho'
    _description = 'Orden de Trabajo'
    _rec_name = 'ot'
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _get_employee_id_domain(self):
        employee = self.env.user.employee_id
        return [('id', '=', employee.id), '|', ('company_id', '=', False),
                ('company_id', '=', employee.company_id.id)]

    ot = fields.Char(
        string="Orden de trabajo",
        readonly=True,
        required=True,
        copy=False,
        default=lambda self: _('New')
    )

    fecha = fields.Date(
        string="Fecha",
        default=lambda s: fields.Date.context_today(s),
        required=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Empleado",
        readonly=True,
        default=_default_employee_id,
        domain=lambda self: self._get_employee_id_domain(),
        check_company=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )

    # Campos principales
    regimen = fields.Many2one('despacho.regimen', 'Régimen', ondelete='restrict')
    regimen_name = fields.Char(compute='_compute_regimen', store=False)
    resolucion_maq = fields.Char('Resolución Maq.')

    propietario = fields.Many2one(
        'res.partner',
        'Propietario',
        ondelete='restrict',
        required=True
    )

    total_gabinete = fields.Float(
        string='Total Gabinete',
        compute='_compute_total_gabinete',
        store=True
    )

    @api.depends('documentos_sin_monto.monto')
    def _compute_total_gabinete(self):
        for record in self:
            record.total_gabinete = sum(record.documentos_sin_monto.mapped('monto'))

    cod_propietario = fields.Char(compute='_compute_cod_propietario', store=False)
    ref_propietario = fields.Char('Referencia del Propietario')
    aduana = fields.Many2one('despacho.aduana', 'Aduana', ondelete='restrict')

    proveedor = fields.Many2one('res.partner', 'Proveedor', ondelete='restrict')
    consignatario = fields.Many2one('res.partner', 'Consignatario', ondelete='restrict')
    transportista = fields.Many2one('res.partner', 'Transportista', ondelete='restrict')

    mercaderias_model = fields.Many2one('despacho.mercaderia', 'Mercadería', ondelete='restrict')
    due = fields.Char('Despacho Único Exportación (DUE)')

    embalaje = fields.Many2one('despacho.embalaje', 'Embalaje')
    cantidad = fields.Float('Cantidad')
    unidad_medida = fields.Many2one('despacho.unidad_medida', 'Unidad de medida')

    peso_neto = fields.Float('Peso Neto')
    peso_bruto = fields.Float('Peso Bruto')

    contenedores = fields.One2many('despacho.contenedor', 'despacho', 'Contenedores')
    documentos = fields.One2many('despacho.documento', 'despacho', 'Documentos')

    desconsolidacion = fields.Char('Desconsolidación')
    manifiesto = fields.Char('Manifiesto')
    barcaza_model = fields.Many2one('despacho.barcaza', 'Barcaza', ondelete='restrict')
    recepciones_datos_id = fields.Many2one(
        'account.voucher',
        string='Recepción Cliente',
        domain=lambda self: [('voucher_type', '=', 'sale')],
        context={'default_voucher_type': 'sale'},
    )

    cnu = fields.Char('CNU')
    acuerdo = fields.Char('Acuerdo')

    # Campos financieros
    fob = fields.Float('FOB')
    flete = fields.Float('Flete')
    seguro = fields.Float('Seguro')
    ajuste = fields.Float('Ajuste')
    descuento = fields.Float('Descuento')

    fecha_oficializacion = fields.Date('Fecha de Oficialización')
    numero_factura = fields.Char('Número de Factura')
    fecha_facturacion = fields.Date('Fecha de Facturación')

    cif = fields.Float('CIF', compute='_compute_cif', store=True)
    moneda = fields.Many2one('despacho.moneda', 'Moneda')
    tc = fields.Float('T/C', compute='_compute_tc', inverse='_inverse_tc')
    cif_guaranies = fields.Float('CIF en Gs', compute='_compute_cif_guaranies', store=True)

    incoterms = fields.Many2one('despacho.incoterms', 'Incoterms')
    presupuesto = fields.One2many('despacho.presupuesto', 'despacho', 'Presupuesto')
    documentos_sin_monto = fields.One2many('despacho.documento_previo', 'despacho', 'Documentos')

    # total del gabinete sin imputar
    total_gabinete = fields.Float(
        string='Total sin Imputar',
        compute='_compute_total_gabinete',
        store=True
    )

    # total del gabinete imputado
    total_gabi_imputar = fields.Float(
        string='Total Imputado',
        compute='_compute_total_gabinete',
        store=True
    )
    
    recepciones_gabi_id = fields.Many2one(
        'account.voucher',
        string='Recepción Proveedor',
        domain=lambda self: [('voucher_type', '=', 'purchase')],
        context={'default_voucher_type': 'purchase'},
    )
    
    # Campos de oficialización
    # total de la oficializacion sin imputar
    total_oficializacion = fields.Float(
        string='Total sin Imputar',
        compute='_compute_totales_oficializacion',
        store=True
    )

    # total de la oficializacion imputado
    total_ofi_imputar = fields.Float(
        string='Total Imputado',
        compute='_compute_totales_oficializacion',
        store=True
    )
    
    recepciones_ofi_id = fields.Many2one(
        'account.voucher',
        string='Recepción Proveedor',
        domain=lambda self: [('voucher_type', '=', 'purchase')],
        context={'default_voucher_type': 'purchase'},
    )
    
    oficial = fields.Char('Despacho oficializado')
    documento = fields.Binary('Despacho oficializado (Carátula)', attachment=True)
    documento_cuerpo = fields.Binary('Despacho oficializado (Cuerpo)', attachment=True)

    canal = fields.Selection([
        ('red', 'Rojo'),
        ('orange', 'Naranja'),
        ('green', 'Verde'),
    ], string="Canal")

    firmado = fields.Boolean('Firmado')
    aduanero = fields.Boolean('Aduanero')
    definitivo = fields.Boolean('Definitivo')

    documentos_oficializacion = fields.One2many(
        'despacho.documento_oficializacion',
        'despacho',
        'Documentos de oficialización'
    )

    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('initial', 'Iniciado'),
        ('oficializado', 'Oficializado'),
        ('liquidado', 'Liquidado'),
    ], string="Estado",
        readonly=False,
        group_expand='_expand_states',
        default='pendiente',
        tracking=True
    )

    attachment_number = fields.Integer(
        'Número de Adjuntos',
        compute='_compute_attachment_number'
    )

    ##### METODOS COMPUTADOS #####
    # def action_crear_recepcion_datos(self):
    #     self.ensure_one()

    #     journal = self.env['account.journal'].search([
    #         ('type', '=', 'sale'),
    #         ('company_id', '=', self.company_id.id)
    #     ], limit=1)

    #     if not journal or not journal.default_account_id:
            # raise UserError("No se encontró un diario de ventas con cuenta predeterminada.")

    #     recepcion = self.env['account.voucher'].create({
    #         'partner_id': self.propietario.id,
    #         'voucher_type': 'sale',
    #         'name': f"Recepción Datos - {self.ot}",
    #         'account_id': journal.default_account_id.id,
    #         'journal_id': journal.id,
    #         'amount': 0.0,
    #     })

    #     self.recepciones_datos_id = recepcion.id

    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.voucher',
    #         'res_id': recepcion.id,
    #         'view_mode': 'form',
    #         'target': 'current',
    #     }


    # def action_crear_recepcion_ofi(self):
    #     self.ensure_one()

    #     if self.recepciones_ofi_id:
    #         return {
    #             'name': 'Recepción Oficialización',
    #             'view_mode': 'form',
    #             'res_model': 'account.voucher',
    #             'type': 'ir.actions.act_window',
    #             'res_id': self.recepciones_ofi_id.id,
    #         }

    #     journal = self.env['account.journal'].search([
    #         ('type', '=', 'purchase'),
    #         ('company_id', '=', self.company_id.id)
    #     ], limit=1)

    #     if not journal or not journal.default_account_id:
    #         raise UserError("No se encontró un diario de compras con cuenta predeterminada.")

    #     recepcion = self.env['account.voucher'].create({
    #         'partner_id': self.propietario.id,
    #         'voucher_type': 'purchase',
    #         'name': f"Recepción Oficialización - {self.ot}",
    #         'account_id': journal.default_account_id.id,
    #         'journal_id': journal.id,
    #         'amount': self.total_ofi_imputar,
    #     })

    #     self.recepciones_ofi_id = recepcion.id

    #     return {
    #         'name': 'Recepción Oficialización',
    #         'view_mode': 'form',
    #         'res_model': 'account.voucher',
    #         'type': 'ir.actions.act_window',
    #         'res_id': recepcion.id,
    #     }


    # def action_crear_recepcion_gabi(self):
    #     self.ensure_one()

    #     journal = self.env['account.journal'].search([
    #         ('type', '=', 'purchase'),
    #         ('company_id', '=', self.company_id.id)
    #     ], limit=1)

    #     if not journal:
    #         raise UserError("No se encontró un diario de compras configurado para la compañía.")

    #     recepcion = self.env['account.voucher'].create({
    #         'partner_id': self.proveedor.id,  # o el campo adecuado
    #         'voucher_type': 'purchase',
    #         'name': f"Recepción - {self.ot}",
    #         'account_id': journal.default_account_id.id,  # Esto resuelve el error
    #         'journal_id': journal.id,
    #     })

    #     self.recepciones_gabi_id = recepcion.id

    #     return {
    #         'name': 'Recepción Gabinete',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.voucher',
    #         'view_mode': 'form',
    #         'res_id': recepcion.id,
    #         'target': 'current',
    #     }


    # aqui se realiza el calculo para ambos campos 'total_oficializacion' y 'total_ofi_imputar'
    @api.depends('documentos_oficializacion.imputar', 'documentos_oficializacion.monto')
    def _compute_totales_oficializacion(self):
        for record in self:
            imputados = 0.0
            no_imputados = 0.0
            for line in record.documentos_oficializacion:
                if line.imputar:
                    imputados += line.monto
                else:
                    no_imputados += line.monto
            record.total_ofi_imputar = imputados
            record.total_oficializacion = no_imputados

    # aqui se realiza el calculo para ambos campos 'total_gabinete' y 'total_gabi_imputar'
    @api.depends('documentos_sin_monto.imputar', 'documentos_sin_monto.monto')
    def _compute_total_gabinete(self):
        for record in self:
            imputados = 0.0
            no_imputados = 0.0
            for line in record.documentos_sin_monto:
                if line.imputar:
                    imputados += line.monto
                else:
                    no_imputados += line.monto
            record.total_gabi_imputar = imputados
            record.total_gabinete = no_imputados

    @api.depends('fob', 'flete', 'seguro', 'ajuste', 'descuento', 'tc')
    def _compute_cif(self):
        for record in self:
            record.cif = record.fob + record.flete + record.seguro + record.ajuste - record.descuento
            record.cif_guaranies = record.cif * record.tc

    @api.depends('tc', 'cif')
    def _compute_cif_guaranies(self):
        for record in self:
            record.cif_guaranies = record.cif * record.tc

    @api.depends('propietario')
    def _compute_cod_propietario(self):
        for record in self:
            record.cod_propietario = record.propietario.codigo

    @api.depends('regimen')
    def _compute_regimen(self):
        for record in self:
            record.regimen_name = record.regimen.name

    @api.onchange('moneda')
    def _compute_tc(self):
        for record in self:
            record.tc = 0
            try:
                url = "https://www.aduana.gov.py/proc.php"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for index, td in enumerate(soup.findAll('td')):
                        if record.moneda.name == 'DOL' and td.contents[0] == 'DOLAR ESTADOUNIDENSE':
                            record.tc = float(
                                soup.findAll('td')[index + 1].contents[0].replace('.', '').replace(',', '.'))
                        if record.moneda.name == 'MCM' and td.contents[0] == 'MONEDA COMUN EUROPEA':
                            record.tc = float(
                                soup.findAll('td')[index + 1].contents[0].replace('.', '').replace(',', '.'))
            except Exception as e:
                _logger.error(f"Error al obtener tipo de cambio: {str(e)}")

    def _inverse_tc(self):
        pass

    # Métodos de estado
    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.onchange('fecha_oficializacion', 'oficial')
    def _compute_oficializacion(self):
        for record in self:
            if record.state != 'liquidado' and record.fecha_oficializacion and record.oficial:
                record.state = 'oficializado'

    @api.onchange('fecha_facturacion', 'numero_factura')
    def _compute_liquidacion(self):
        for record in self:
            if record.fecha_facturacion and record.numero_factura:
                record.state = 'liquidado'

    def action_confirm(self):
        for rec in self:
            if rec.state == 'initial':
                rec.state = 'presupuestado'
            elif rec.state == 'presupuestado':
                rec.state = 'pendiente'
            elif rec.state == 'pendiente':
                rec.state = 'aprobado'
            elif rec.state == 'aprobado':
                rec.state = 'listo'
            elif rec.state == 'listo':
                rec.state = 'oficializado'
            elif rec.state == 'oficializado':
                rec.state = 'finiquitado'
            elif rec.state == 'finiquitado':
                rec.state = 'liquidado'

    # Métodos CRUD
    @api.model
    def create(self, vals):
        if vals.get('ot', _('New')) == _('New'):
            vals['ot'] = self.env['ir.sequence'].next_by_code('despacho.despacho.sequence') or _('New')
            codigo_cliente = self.env['res.partner'].search_read(
                [('id', '=', vals['propietario'])],
                ['codigo'],
                limit=1
            )
            if codigo_cliente and codigo_cliente[0]['codigo']:
                numero_ot = vals['ot']
                vals['ot'] = numero_ot[:2] + codigo_cliente[0]['codigo'] + numero_ot[2:]
        return super().create(vals)

    @api.onchange('regimen')
    def regimen_onchange(self):
        for record in self:
            documentos_lines = [(5, 0, 0)]
            tipos_documentos = self.env['despacho.tipo_documento'].search([('regimen', '!=', False)])

            for tipo in tipos_documentos:
                if record.regimen in tipo.regimen:
                    documentos_lines.append((0, 0, {'tipo': tipo.id}))

            record.documentos = documentos_lines

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Lógica para documentos por defecto
        return res

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'despacho.despacho'), ('res_id', '=', self.id)],
            ['res_id'],
            ['res_id']
        )
        self.attachment_number = attachment_data[0]['res_id_count'] if attachment_data else 0

    def action_get_attachment_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Adjuntos',
            'view_mode': 'kanban,tree,form',
            'res_model': 'ir.attachment',
            'domain': [('res_model', '=', 'despacho.despacho'), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': 'despacho.despacho',
                'default_res_id': self.id,
                'create': False
            }
        }

    def button_imprimir_ot_web(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f"/report/html/despacho.report_print_ot_web_template/{self.id}",
            'target': 'new'
        }

    def action_despachos_report(self):
        despachos_ids = self.env.context.get('active_ids', [])
        if not despachos_ids:
            return

    factura_cliente_id = fields.Many2one('account.move', string='Factura Cliente', readonly=True)

    # boton para crear facturas
    def action_crear_factura_cliente(self):
        for rec in self:
            if rec.factura_cliente_id:
                return {
                    'name': 'Factura Cliente',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_cliente_id.id,
                }

            factura = self.env['account.move'].create({
                'partner_id': rec.propietario.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura generada desde despacho',
                    'quantity': 1,
                    'price_unit': rec.total_oficializacion,
                    'account_id': self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id,
                })],
            })

            rec.write({
                'numero_factura': factura.name,
                'fecha_facturacion': factura.invoice_date,
                'factura_cliente_id': factura.id,
            })

            return {
                'name': 'Factura Cliente',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': factura.id,
            }


class Documento(models.Model):
    _name = 'despacho.documento'
    _description = 'Documento de Despacho'

    tipo = fields.Many2one('despacho.tipo_documento', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    archivo = fields.Binary('Archivo', attachment=True)
    original = fields.Boolean('Original')
    visado = fields.Boolean('Visado')
    fecha = fields.Date('Fecha')
    despacho = fields.Many2one('despacho.despacho', 'Despacho', ondelete='cascade')
    imputar = fields.Boolean('Imputar')

    def name_get(self):
        return [(record.id, f"{record.tipo.name} - {record.numero}" if record.numero else record.tipo.name)
                for record in self]

    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    def action_crear_factura_proveedor(self):
        for rec in self:
            # Si ya existe la factura asociada, se redirecciona a ella
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }
            # Si no existe, se crea la factura
            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,  # Ajustá este valor según corresponda
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
                'fecha': factura.invoice_date,
                'factura_proveedor_id': factura.id,
            })

            return {
                'name': 'Factura Proveedor',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': factura.id,
            }


class Presupuesto(models.Model):
    _name = 'despacho.presupuesto'
    _description = 'Presupuesto de Despacho'

    despacho = fields.Many2one('despacho.despacho', 'Despacho')
    despacho_provisorio_nro = fields.Char('Despacho provisorio Nro')
    despacho_provisorio = fields.Binary('Despacho provisorio (carátula)', attachment=True)
    despacho_provisorio_continuacion = fields.Binary('Despacho provisorio (cuerpo)', attachment=True)
    despacho_provisorio_fecha = fields.Date('Fecha')


class DocumentoPrevio(models.Model):
    _name = 'despacho.documento_previo'
    _description = 'Documento Previo de Despacho'

    tipo = fields.Many2one('despacho.tipo_documento_previo', 'Tipo', ondelete='cascade')
    numero = fields.Char('Número')
    archivo = fields.Binary('Archivo', attachment=True)
    fecha = fields.Date('Fecha')
    vencimiento = fields.Date('Vencimiento')
    despacho = fields.Many2one('despacho.despacho', 'Despacho')
    monto = fields.Float('Monto')
    pagado_por = fields.Selection([
        ('cliente', 'Cliente'),
        ('agencia', 'Agencia')
    ])
    op = fields.Many2one('despacho.ordenpago', 'Orden de pago')
    hr_expense = fields.Many2one('hr.expense', 'Gasto')
    imputar = fields.Boolean('Imputar')

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.monto > 0:
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': record.monto,
                    'fecha': fields.Date.today(),
                    'vencimiento': record.vencimiento or fields.Date.today()
                })
        return records

    def write(self, vals):
        if 'monto' in vals and vals['monto'] > 0:
            for record in self:
                if record.op:
                    record.op.unlink()
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': vals['monto'],
                    'fecha': fields.Date.today(),
                    'vencimiento': vals.get('vencimiento', record.vencimiento) or fields.Date.today()
                })
        return super().write(vals)

    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    def action_crear_factura_proveedor(self):
        for rec in self:
            # Si ya existe la factura asociada, se redirecciona a ella
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }
            # Si no existe, se crea la factura
            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,  # Ajustá este valor según corresponda
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
                'fecha': factura.invoice_date,
                'factura_proveedor_id': factura.id,
            })

            return {
                'name': 'Factura Proveedor',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': factura.id,
            }



class DocumentoOficializacion(models.Model):
    _name = 'despacho.documento_oficializacion'
    _description = 'Documento de Oficialización de Despacho'

    tipo = fields.Many2one('despacho.tipo_documento_oficializacion', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    documento = fields.Binary('Documento', attachment=True)
    monto = fields.Float('Monto')
    pagado_por = fields.Selection([
        ('cliente', 'Cliente'),
        ('agencia', 'Agencia')
    ])
    despacho = fields.Many2one('despacho.despacho', 'Despacho')
    op = fields.Many2one('despacho.ordenpago', 'Orden de pago')
    hr_expense = fields.Many2one('hr.expense', 'Gasto')
    imputar = fields.Boolean('Imputar')

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.monto > 0:
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': record.monto,
                    'fecha': fields.Date.today(),
                    'vencimiento': fields.Date.today()
                })
        return records

    def write(self, vals):
        if 'monto' in vals and vals['monto'] > 0:
            for record in self:
                if record.op:
                    record.op.unlink()
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': vals['monto'],
                    'fecha': fields.Date.today(),
                    'vencimiento': fields.Date.today()
                })
        return super().write(vals)

    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    def action_crear_factura_proveedor(self):
        for rec in self:
            # Si ya existe la factura asociada, se redirecciona a ella
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }
            # Si no existe, se crea la factura
            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,  # Ajustá este valor según corresponda
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
                'fecha': factura.invoice_date,
                'factura_proveedor_id': factura.id,
            })

            return {
                'name': 'Factura Proveedor',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': factura.id,
            }