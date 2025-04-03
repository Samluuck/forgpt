from odoo import models, fields, api, _
from datetime import datetime
import requests
from bs4 import BeautifulSoup

import xlwt
from xlsxwriter.workbook import Workbook
import base64


# VISTAS CREADAS
class Contenedor(models.Model):
    _name = 'despachos.contenedor'
    _description = 'despachos.contenedor'

    tipo = fields.Many2one('despachos.tipo_contenedor', 'Tipo', ondelete='restrict')
    numero = fields.Char()

    despacho = fields.Many2one('despachos.despacho', 'Despacho')

    def name_get(self):
        result = []
        for record in self:
            record_name = record.numero
            result.append((record.id, record_name))
        return result


class Mercaderia(models.Model):
    _name = 'despachos.mercaderia'
    _description = 'despachos.mercaderia'

    name = fields.Char(_('Descripción'))


class UnidadMedida(models.Model):
    _name = 'despachos.unidad_medida'
    _description = 'Unidad Medida'

    name = fields.Char(_('Descripción'))


class Barcaza(models.Model):
    _name = 'despachos.barcaza'
    _description = 'despachos.barcaza'

    name = fields.Char(_('Descripción'))


class Despacho(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'despachos.despacho'
    _description = 'Orden de trabajo'
    _rec_name = 'ot'
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _get_employee_id_domain(self):
        employee = self.env.user.employee_id
        res = [('id', '=', employee.id), '|', ('company_id', '=', False),
               ('company_id', '=', employee.company_id.id)]
        return res

    ot = fields.Char(string=_("Orden de trabajo"), readonly=True, required=True, copy=False,
                     default=lambda self: _('New'))
    fecha = fields.Date(string="Fecha", default=lambda s: fields.Date.context_today(s), required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True,
                                  default=_default_employee_id,
                                  domain=lambda self: self._get_employee_id_domain(), check_company=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.user.company_id)

    regimen = fields.Many2one('despachos.regimen', 'Regimen', ondelete='restrict')
    regimen_name = fields.Char(compute='_compute_regimen', store=False)
    resolucion_maq = fields.Char(_('Resolucion Maq.'))

    propietario = fields.Many2one('res.partner', 'Propietario', ondelete='restrict', required=True)
    cod_propietario = fields.Char(compute='compute_cod_propietario', store=False)
    ref_propietario = fields.Char(_('Referencia del Propietario'))
    aduana = fields.Many2one('despachos.aduana', 'Aduana', ondelete='restrict')

    proveedor = fields.Many2one('res.partner', 'Proveedor', ondelete='restrict')
    consignatario = fields.Many2one('res.partner', 'Consignatario', ondelete='restrict')
    transportista = fields.Many2one('res.partner', 'Transportista', ondelete='restrict')

    mercaderias_model = fields.Many2one('despachos.mercaderia', 'Mercaderia', ondelete='restrict')
    due = fields.Char(_('Despacho Unico Exportacion (DUE)'))

    # TODO esto no se entiende
    embalaje = fields.Many2one('despachos.embalaje', 'Embalaje')
    cantidad = fields.Float('Cantidad')
    unidad_medida = fields.Many2one('despachos.unidad_medida', 'Unidad de medida')

    peso_neto = fields.Float('Peso Neto')
    peso_bruto = fields.Float('Peso Bruto')

    contenedores = fields.One2many('despachos.contenedor', 'despacho', 'Contenedores')

    # Modulo de datos
    documentos = fields.One2many('despachos.documento', 'despacho', _('Documentos'))

    desconsolidacion = fields.Char('Desconsolidacion')
    manifiesto = fields.Char('Manifiesto')
    barcaza_model = fields.Many2one('despachos.barcaza', 'Barcaza', ondelete='restrict')

    cnu = fields.Char('CNU')
    acuerdo = fields.Char('Acuerdo')

    fob = fields.Float('FOB')
    flete = fields.Float('Flete')
    seguro = fields.Float('Seguro')
    ajuste = fields.Float('Ajuste')
    descuento = fields.Float('Descuento')
    fecha_oficializacion = fields.Date(string="Fecha de Oficialización",
                                       required=False)

    numero_factura = fields.Char(required=False, string="Número de Factura")
    fecha_facturacion = fields.Date(string="Fecha de Facturación",
                                required=False)

    @api.onchange('fob', 'flete', 'seguro', 'ajuste', 'descuento', 'tc')
    def _compute_cif(self):
        for record in self:
            record.cif = record.fob + record.flete + record.seguro + record.ajuste - record.descuento
            record.cif_guaranies = record.cif * record.tc

    cif = fields.Float('CIF')

    moneda = fields.Many2one('despachos.moneda', 'Moneda')

    def button_imprimir_ot_web(self):
        for record in self:
            return {
                'type': 'ir.actions.act_url',
                'url': "/report/html/despachos.report_print_ot_web_template/" + str(record.id),
                'target': 'new',
                'res_id': record.id
            }

    def action_despachos_report(self):
        despachos_ids = self.env['despachos.despacho'].browse(self.env.context.get('active_ids'))
        print(despachos_ids, '<<<<<< despacho ids')

        inicio = None
        fin = None
        for despacho in despachos_ids:
            if inicio is None:
                inicio = despacho.fecha_oficializacion

            fin = despacho.fecha_oficializacion

        # Despachos oficializados
        query = """select ru.login, count(*) from despachos_despacho 
        left join res_users ru on despachos_despacho.write_uid = ru.id
        where despachos_despacho.oficial is not null
        and despachos_despacho.fecha_oficializacion <= '%s'
        and despachos_despacho.fecha_oficializacion >= '%s'
        group by(ru.login);""" % (inicio, fin)
        self.env.cr.execute(query)
        despachos_oficializados = self.env.cr.fetchall()

        # Documentos despachos
        query = """select ru.login, count(*) from despachos_documento
        left join res_users ru on despachos_documento.write_uid = ru.id
        where despachos_documento.despacho in (
            select despachos_despacho.id from despachos_despacho
        where despachos_despacho.oficial is not null
        and despachos_despacho.fecha_oficializacion <= '%s'
        and despachos_despacho.fecha_oficializacion >= '%s'
        )
        group by ru.login;""" % (inicio, fin)
        self.env.cr.execute(query)
        documentos_despachos = self.env.cr.fetchall()

        # Documentos previos
        query = """select ru.login, count(*) from despachos_documento_previo
                                           left join res_users ru on ru.id = despachos_documento_previo.write_uid
        where despachos_documento_previo.despacho in (
            select despachos_despacho.id from despachos_despacho
            where despachos_despacho.oficial is not null
              and despachos_despacho.fecha_oficializacion <= '%s'
              and despachos_despacho.fecha_oficializacion >= '%s'
        )
        group by ru.login;""" % (inicio, fin)
        self.env.cr.execute(query)
        documentos_previos = self.env.cr.fetchall()

        # Documentos oficialización
        query = """select ru.login, count(*) from despachos_documento_previo_con_monto
                                   left join res_users ru on despachos_documento_previo_con_monto.write_uid = ru.id
        where despachos_documento_previo_con_monto.despacho in (
            select despachos_despacho.id from despachos_despacho
            where despachos_despacho.oficial is not null
              and despachos_despacho.fecha_oficializacion <= '%s'
              and despachos_despacho.fecha_oficializacion >= '%s'
                )
        group by ru.login;""" % (inicio, fin)
        self.env.cr.execute(query)
        documentos_oficializacion = self.env.cr.fetchall()

        # Totales
        query = """select ru.login, count(*) from despachos_documento_oficializacion left join res_users ru on despachos_documento_oficializacion.write_uid = ru.id
        where despachos_documento_oficializacion.despacho in (
            select despachos_despacho.id from despachos_despacho
            where despachos_despacho.oficial is not null
              and despachos_despacho.fecha_oficializacion <= '%s'
              and despachos_despacho.fecha_oficializacion >= '%s'
        )
        group by ru.login;""" % (inicio, fin)
        self.env.cr.execute(query)
        totales = self.env.cr.fetchall()

        # retornar archivo excel


    @api.onchange('moneda')
    def _compute_tc(self):
        for record in self:
            record.tc = 0
            url = "https://www.aduana.gov.py/proc.php"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for index, td in enumerate(soup.findAll('td')):
                    if record.moneda.name == 'DOL' and td.contents[0] == 'DOLAR ESTADOUNIDENSE':
                        record.tc = float(soup.findAll('td')[index + 1].contents[0].replace('.', '').replace(',', '.'))
                    if record.moneda.name == 'MCM' and td.contents[0] == 'MONEDA COMUN EUROPEA':
                        record.tc = float(soup.findAll('td')[index + 1].contents[0].replace('.', '').replace(',', '.'))

    def _inverse_tc(self):
        for record in self:
            pass

    tc = fields.Float('T/C', compute='_compute_tc', inverse='_inverse_tc')

    @api.depends('tc', 'cif')
    def _compute_cif_guaranies(self):
        for record in self:
            record.cif_guaranies = record.cif * record.tc

    cif_guaranies = fields.Float('CIF en Gs', compute='_compute_cif_guaranies')

    incoterms = fields.Many2one('despachos.incoterms', 'Incoterms')

    # Modulo de Gabinete
    presupuesto = fields.One2many('despachos.presupuesto', 'despacho', 'Presupuesto')

    # Modulo Previo
    documentos_sin_monto = fields.One2many('despachos.documento_previo', 'despacho', _('Documentos'))

    # Modulo de Oficializacion
    oficial = fields.Char(_('Despacho oficializado'))
    documento = fields.Binary(_('Despacho oficializado (Caratula)'), attachment=True)
    documento_cuerpo = fields.Binary(_('Despacho oficializado (Cuerpo)'), attachment=True)
    canal = fields.Selection([
        ('red', _('Rojo')),
        ('orange', _('Naranja')),
        ('green', _('Verde')),
    ])
    firmado = fields.Boolean(_('Firmado'))
    aduanero = fields.Boolean(_('Aduanero'))
    definitivo = fields.Boolean(_('Definitivo'))

    documentos_oficializacion = fields.One2many('despachos.documento_oficializacion', 'despacho', _('Documentos de oficialización'))

    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('initial', 'Iniciado'),
        # ('cargado', 'Datos cargados'),
        # ('previo', 'Gabinete'),
        ('oficializado', 'Oficializado'),
        # ('finiquitado', 'Finiquitado'),
        ('liquidado', 'Liquidado'),
    ], string="Estado", readonly=False, group_expand='_expand_states', default='pendiente')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.onchange('fecha_oficializacion', 'oficial')
    def _compute_oficializacion(self):
        for record in self:
            if record.state != 'liquidado' and record.fecha_oficializacion is not False and record.oficial is not False:
                record.state = 'oficializado'

    @api.onchange('fecha_facturacion', 'numero_factura')
    def _compute_liquidacion(self):
        for record in self:
            if record.fecha_facturacion is not False and record.numero_factura is not False:
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

    @api.model
    def create(self, vals):
        for record in self:
            print(record)
        if vals.get('ot', _('New')) == _('New'):
            vals['ot'] = self.env['ir.sequence'].next_by_code(
                'despachos.despacho.sequence') or _('New')
            codigo_cliente = self.env['res.partner'].search_read([('id', '=', vals['propietario'])])[-1]['codigo']
            if codigo_cliente:
                numero_ot = vals['ot']
                numero_ot = numero_ot[:2] + codigo_cliente + numero_ot[2:]
                vals['ot'] = numero_ot

        result = super(Despacho, self).create(vals)
        return result

    @api.depends('propietario')
    def compute_cod_propietario(self):
        for record in self:
            record.cod_propietario = record.propietario.codigo

    @api.depends('regimen')
    def _compute_regimen(self):
        for record in self:
            record.regimen_name = record.regimen.name

    @api.onchange('regimen')
    def regimen_onchange(self):
        for record in self:
            # Recorremos los documentos cargados y limpiamos los que no deben estar
            documentos_lines = [(5, 0, 0)]

            tipos_documentos = self.env['despachos.tipo_documento'].search([('regimen', '!=', False)])
            for tipo in tipos_documentos:
                if self.regimen in tipo.regimen:
                    line = (0, 0, {
                        'tipo': tipo.id,
                    })
                    documentos_lines.append(line)
            record.documentos = documentos_lines

            documentos_previos_lines = [(5, 0, 0)]
            tipos_documentos_previos = self.env['despachos.tipo_documento_previo'].search([('regimen', '!=', False)])
            for tipo in tipos_documentos_previos:
                if self.regimen in tipo.regimen:
                    line = (0, 0, {
                        'tipo': tipo.id
                    })
                    documentos_previos_lines.append(line)

            documentos_oficializacion = [(5, 0, 0)]
            tipos_documentos_oficializacion = self.env['despachos.tipo_documento_oficializacion'].search(
                [('regimen', '!=', False)])
            for tipo in tipos_documentos_oficializacion:
                if self.regimen in tipo.regimen:
                    line = (0, 0, {
                        'tipo': tipo.id
                    })
                    documentos_oficializacion.append(line)

            record.update({
                'documentos': documentos_lines,
                'documentos_sin_monto': documentos_previos_lines,
                'documentos_oficializacion': documentos_oficializacion
            })

    @api.model
    def default_get(self, fields_list):
        res = super(Despacho, self).default_get(fields_list)
        documentos_lines = []

        tipos_documentos = self.env['despachos.tipo_documento'].search([])
        for tipo in tipos_documentos:

            if tipo.regimen != False and self.regimen and False and tipo.regimen == self.regimen:
                line = (0, 0, {
                    'tipo': tipo.id,
                })
                documentos_lines.append(line)

        documentos_previos_lines = []
        tipos_documentos_previos = self.env['despachos.tipo_documento_previo'].search([])
        for tipo in tipos_documentos_previos:
            if tipo.regimen != False and self.regimen and False and tipo.regimen == self.regimen:
                line = (0, 0, {
                    'tipo': tipo.id
                })
                documentos_previos_lines.append(line)

        documentos_oficializacion = []
        tipos_documentos_oficializacion = self.env['despachos.tipo_documento_oficializacion'].search([])
        for tipo in tipos_documentos_oficializacion:
            if tipo.regimen != False and self.regimen and False and tipo.regimen == self.regimen:
                line = (0, 0, {
                    'tipo': tipo.id
                })
                documentos_oficializacion.append(line)

        res.update({
            'documentos': documentos_lines,
            'documentos_sin_monto': documentos_previos_lines,
            'documentos_oficializacion': documentos_oficializacion
        })

        return res

    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'despachos.despacho'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for despacho in self:
            despacho.attachment_number = attachment.get(despacho.id, 0)

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'despachos.despacho'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'despachos.despacho', 'default_res_id': self.id}
        return res


class Documento(models.Model):
    _name = 'despachos.documento'
    _description = 'despachos.documento'

    tipo = fields.Many2one('despachos.tipo_documento', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    archivo = fields.Binary('Archivo', attachment=True)
    original = fields.Boolean('Original')
    visado = fields.Boolean('Visado')
    fecha = fields.Date('Fecha')

    despacho = fields.Many2one('despachos.despacho', 'Despacho', ondelete='cascade')
    imputar = fields.Boolean('Imputar')

    def name_get(self):
        result = []
        for record in self:
            record_name = record.tipo.name
            if record.numero:
                record_name = record.tipo.name + ' - ' + record.numero
            result.append((record.id, record_name))
        return result


class Presupuesto(models.Model):
    _name = 'despachos.presupuesto'
    _description = 'despachos.presupuesto'

    despacho = fields.Many2one('despachos.despacho', 'Despacho')

    despacho_provisorio_nro = fields.Char('Despacho provisorio Nro')
    despacho_provisorio = fields.Binary('Despacho provisorio (carátula)', attachment=True)
    despacho_provisorio_continuacion = fields.Binary('Despacho provisorio (cuerpo)', attachment=True)
    despacho_provisorio_fecha = fields.Date('Fecha')


class DocumentoPrevio(models.Model):
    _name = 'despachos.documento_previo'
    _description = 'despachos.documento_previo'

    tipo = fields.Many2one('despachos.tipo_documento_previo',
                           'Tipo', ondelete='cascade')
    numero = fields.Char(_('Número'))
    archivo = fields.Binary(_('Archivo'), attachment=True)

    fecha = fields.Date(_('Fecha'))
    vencimiento = fields.Date(_('Vencimiento'))

    despacho = fields.Many2one('despachos.despacho', _('Despacho'))

    monto = fields.Float(_('Monto'))

    pagado_por = fields.Selection([
        ('cliente', 'Cliente'),
        ('agencia', 'Agencia')
    ])

    op = fields.Many2one('despachos.ordenpago', _('Orden de pago'))
    hr_expense = fields.Many2one('hr.expense', _('Expense'))

    imputar = fields.Boolean('Imputar')

    @api.model
    def create(self, vals_list):
        if vals_list.get('monto', 0) > 0:
            record = self.env['despachos.ordenpago'].create({
                'despacho': vals_list.get('despacho'),
                'monto': vals_list.get('monto', 0),
                'fecha': datetime.today(),
                'vencimiento': vals_list.get('vencimiento', datetime.today())
            })
            vals_list['op'] = record.id
        return super(DocumentoPrevio, self).create(vals_list)

    @api.model
    def write(self, vals):
        if vals.get('monto', 0) > 0:
            if self.op:
                self.env['despachos.ordenpago'].search([('id', '=', self.op.id)]).unlink()
            record = self.env['despachos.ordenpago'].create({
                'despacho': vals.get('despacho'),
                'monto': vals.get('monto', 0),
                'fecha': datetime.today(),
                'vencimiento': vals.get('vencimiento', datetime.today())
            })
            vals['op'] = record.id
        return super(DocumentoPrevio, self).write(vals)

    @api.model
    def unlink(self):
        return super(DocumentoPrevio, self).unlink()


class DocumentoOficializacion(models.Model):
    _name = 'despachos.documento_oficializacion'
    _description = 'despachos.documento_oficializacion'

    tipo = fields.Many2one('despachos.tipo_documento_oficializacion',
                           'Tipo', ondelete='restrict')
    numero = fields.Char(_('Numero'))
    documento = fields.Binary(_('Documento'), attachment=True)
    monto = fields.Float(_('Monto'))

    pagado_por = fields.Selection([
        ('cliente', _('Cliente')),
        ('agencia', _('Agencia'))
    ])

    despacho = fields.Many2one('despachos.despacho', _('Despacho'))

    op = fields.Many2one('despachos.ordenpago', _('Orden de pago'))
    hr_expense = fields.Many2one('hr.expense', _('Expense'))

    imputar = fields.Boolean('Imputar')

    @api.model
    def create(self, vals_list):
        if vals_list.get('monto', 0) > 0:
            record = self.env['despachos.ordenpago'].create({
                'despacho': vals_list.get('despacho'),
                'monto': vals_list.get('monto', 0),
                'fecha': datetime.today(),
                'vencimiento': vals_list.get('vencimiento', datetime.today())
            })
            vals_list['op'] = record.id

        return super(DocumentoOficializacion, self).create(vals_list)

    @api.model
    def write(self, vals):
        if vals.get('monto', 0) > 0:
            if self.op:
                self.env['despachos.ordenpago'].search([('id', '=', self.op.id)]).unlink()
            record = self.env['despachos.ordenpago'].create({
                'despacho': vals.get('despacho'),
                'monto': vals.get('monto', 0),
                'fecha': datetime.today(),
                'vencimiento': vals.get('vencimiento', datetime.today())
            })
            vals['op'] = record.id
        return super(DocumentoOficializacion, self).write(vals)

    @api.model
    def unlink(self):
        return super(DocumentoOficializacion, self).unlink()
