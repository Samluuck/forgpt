from odoo import models, fields, api, _
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import base64
import io
import time
from PyPDF2 import PdfMerger
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Contenedor(models.Model):
    _name = 'despacho.contenedor'
    _description = 'Contenedor de Despacho'

    tipo = fields.Many2one('despacho.tipo_contenedor', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    despacho = fields.Many2one('despacho.despacho', 'Despacho')

    def name_get(self):
        return [(record.id, record.numero or '') for record in self]


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

    # CAMPOS BÁSICOS
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
        default=lambda self: self._default_employee_id(),
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
        domain=[('voucher_type', '=', 'sale')],
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
    fecha_facturacion = fields.Date('Fecha de Liquidación', store=True)

    cif = fields.Float('CIF', compute='_compute_cif', store=True)
    moneda = fields.Many2one('despacho.moneda', 'Moneda')
    cif_guaranies = fields.Float('CIF en Gs', compute='_compute_cif_guaranies', store=True)

    incoterms = fields.Many2one('despacho.incoterms', 'Incoterms')
    presupuesto = fields.One2many('despacho.presupuesto', 'despacho', 'Presupuesto')
    documentos_sin_monto = fields.One2many('despacho.documento_previo', 'despacho', 'Documentos')

    # CAMPOS ADICIONALES
    pais_origen = fields.Char(string="Pais Origen")
    crt = fields.Char(string="CRT / BL / AWB")
    partida_arancelaria = fields.Char(string="Partida Arancelaria")
    imponible_usd = fields.Float(string="Imponible USD")

    documentos_legajo = fields.One2many(
        'despacho.documento_legajo',
        'despacho_id',
        string='Documentos Legajo',
        copy=False
    )

    documentos_unificados = fields.One2many(
        'despacho.documento_unificado',
        'despacho_id',
        string='Documentos Unificados',
        copy=False
    )

    # CAMPOS COMPUTADOS DE TOTALES
    total_datos = fields.Float(
        string='Total sin Imputar',
        compute='_compute_total_datos',
        store=True
    )

    total_datos_imputar = fields.Float(
        string='Total Imputado',
        compute='_compute_total_datos',
        store=True
    )

    total_gabinete = fields.Float(
        string='Total sin Imputar',
        compute='_compute_total_gabinete',
        store=True
    )

    total_gabi_imputar = fields.Float(
        string='Total Imputado',
        compute='_compute_total_gabinete',
        store=True
    )

    recepciones_gabi_id = fields.Many2one(
        'account.voucher',
        string='Recepción Proveedor',
        domain=[('voucher_type', '=', 'purchase')],
        context={'default_voucher_type': 'purchase'},
    )

    total_oficializacion = fields.Float(
        string='Total sin Imputar',
        compute='_compute_totales_oficializacion',
        store=True
    )

    total_ofi_imputar = fields.Float(
        string='Total Imputado',
        compute='_compute_totales_oficializacion',
        store=True
    )

    recepciones_ofi_id = fields.Many2one(
        'account.voucher',
        string='Recepción Proveedor',
        domain=[('voucher_type', '=', 'purchase')],
        context={'default_voucher_type': 'purchase'},
    )

    oficial = fields.Char('Despacho oficializado')
    tc = fields.Float(
        string='T/C',
        compute='_compute_tc',
        inverse='_inverse_tc',
        store=True,
        default=0.0,
        required=False
    )

    documento = fields.Binary('Despacho oficializado (Carátula)', attachment=True)

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

    factura_cliente_id = fields.Many2one('account.move', string='Factura Cliente', readonly=True)

    # Campo computado para número de liquidación
    numero_liquidacion = fields.Char(
        string='Número de Liquidación',
        compute='_compute_numero_liquidacion',
        store=True,
        help="Formato: LQWWWW.XX.YY.ZZ donde WWWW es el número de OT y XX.YY.ZZ es día.mes.año"
    )

    # MÉTODOS AUXILIARES
    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _get_employee_id_domain(self):
        employee = self.env.user.employee_id
        return [('id', '=', employee.id), '|', ('company_id', '=', False),
                ('company_id', '=', employee.company_id.id)]

    # MÉTODOS COMPUTADOS
    @api.depends('ot', 'fecha_facturacion')
    def _compute_numero_liquidacion(self):
        for record in self:
            if record.ot and record.fecha_facturacion:
                fecha_str = record.fecha_facturacion.strftime('%d.%m.%y')
                record.numero_liquidacion = f"LQ{record.ot}.{fecha_str}"
            else:
                record.numero_liquidacion = ""

    @api.depends('documentos.imputar', 'documentos.monto')
    def _compute_total_datos(self):
        for record in self:
            imputados = 0.0
            no_imputados = 0.0
            for line in record.documentos:
                if line.imputar:
                    imputados += line.monto or 0.0
                else:
                    no_imputados += line.monto or 0.0
            record.total_datos_imputar = imputados
            record.total_datos = no_imputados

    @api.depends('documentos_sin_monto.imputar', 'documentos_sin_monto.monto')
    def _compute_total_gabinete(self):
        for record in self:
            imputados = 0.0
            no_imputados = 0.0
            for line in record.documentos_sin_monto:
                if line.imputar:
                    imputados += line.monto or 0.0
                else:
                    no_imputados += line.monto or 0.0
            record.total_gabi_imputar = imputados
            record.total_gabinete = no_imputados

    @api.depends('documentos_oficializacion.imputar', 'documentos_oficializacion.monto')
    def _compute_totales_oficializacion(self):
        for record in self:
            imputados = 0.0
            no_imputados = 0.0
            for line in record.documentos_oficializacion:
                if line.imputar:
                    imputados += line.monto or 0.0
                else:
                    no_imputados += line.monto or 0.0
            record.total_ofi_imputar = imputados
            record.total_oficializacion = no_imputados

    @api.depends('fob', 'flete', 'seguro', 'ajuste', 'descuento', 'tc')
    def _compute_cif(self):
        for record in self:
            fob = record.fob or 0.0
            flete = record.flete or 0.0
            seguro = record.seguro or 0.0
            ajuste = record.ajuste or 0.0
            descuento = record.descuento or 0.0
            tc = record.tc or 0.0
            
            record.cif = fob + flete + seguro + ajuste - descuento
            record.cif_guaranies = record.cif * tc

    @api.depends('tc', 'cif')
    def _compute_cif_guaranies(self):
        for record in self:
            cif = record.cif or 0.0
            tc = record.tc or 0.0
            record.cif_guaranies = cif * tc

    @api.depends('propietario')
    def _compute_cod_propietario(self):
        for record in self:
            record.cod_propietario = record.propietario.codigo if record.propietario else ''

    @api.depends('regimen')
    def _compute_regimen(self):
        for record in self:
            record.regimen_name = record.regimen.name if record.regimen else ''

    def _compute_attachment_number(self):
        for record in self:
            attachment_data = self.env['ir.attachment'].read_group(
                [('res_model', '=', 'despacho.despacho'), ('res_id', '=', record.id)],
                ['res_id'],
                ['res_id']
            )
            record.attachment_number = attachment_data[0]['res_id_count'] if attachment_data else 0

    # MÉTODOS DE NEGOCIO
    def importar_documentos_legajo(self):
        """Método para importar documentos al legajo desde diferentes orígenes, solo los marcados para imputar"""
        for rec in self:
            rec.documentos_legajo.unlink()

            modelos = [
                ('documentos', 'datos', 'archivo', 'imputar', 'despacho.documento', 'factura_proveedor_id'),
                ('documentos_sin_monto', 'gabinete', 'archivo', 'imputar', 'despacho.documento_previo', 'factura_proveedor_id'),
                ('documentos_oficializacion', 'oficializacion', 'archivo', 'imputar', 'despacho.documento_oficializacion', 'factura_proveedor_id'),
                ('presupuesto', 'presupuesto', 'despacho_provisorio', None, 'despacho.presupuesto', None),
            ]

            for campo_relacion, origen, campo_binario, campo_imputar, modelo_origen, campo_factura in modelos:
                documentos = getattr(rec, campo_relacion, None)
                if not documentos:
                    continue
                    
                for doc in documentos:
                    if campo_imputar is None or getattr(doc, campo_imputar, False):
                        archivo = getattr(doc, campo_binario, False)
                        if archivo:
                            imputado = getattr(doc, campo_imputar, False) if campo_imputar else False
                            factura_id = False
                            if campo_factura:
                                factura = getattr(doc, campo_factura, False)
                                factura_id = factura.id if factura else False

                            rec.env['despacho.documento_legajo'].create({
                                'name': doc.numero or (doc.tipo.name if hasattr(doc, 'tipo') and doc.tipo else 'Documento'),
                                'archivo': archivo,
                                'origen': origen,
                                'despacho_id': rec.id,
                                'fecha_documento': getattr(doc, 'fecha', fields.Date.today()),
                                'tipo_documento': doc.tipo.name if hasattr(doc, 'tipo') and doc.tipo else origen.upper(),
                                'monto': getattr(doc, 'monto', 0.0),
                                'imputado': imputado,
                                'documento_origen_id': doc.id,
                                'modelo_origen': modelo_origen,
                                'factura_id': factura_id,
                            })

            # Importar factura de cliente si existe
            if rec.factura_cliente_id:
                rec.env['despacho.documento_legajo'].create({
                    'name': f"Factura Cliente {rec.factura_cliente_id.name}",
                    'archivo': False,
                    'origen': 'liquidacion',
                    'despacho_id': rec.id,
                    'fecha_documento': rec.factura_cliente_id.invoice_date,
                    'tipo_documento': 'Factura liquidacion',
                    'monto': rec.factura_cliente_id.amount_total,
                    'imputado': True,
                    'factura_id': rec.factura_cliente_id.id,
                })

    def importar_documentos_unificados(self):
        for rec in self:
            rec.documentos_unificados.unlink()

            modelos = [
                ('documentos', 'datos', 'archivo'),
                ('documentos_sin_monto', 'gabinete', 'archivo'),
                ('documentos_oficializacion', 'oficializacion', 'documento'),
            ]

            for campo_relacion, origen, campo_binario in modelos:
                documentos = getattr(rec, campo_relacion, None)
                if not documentos:
                    continue
                    
                for doc in documentos:
                    archivo = getattr(doc, campo_binario, False)
                    if archivo:
                        rec.env['despacho.documento_unificado'].create({
                            'name': doc.numero or (doc.tipo.name if hasattr(doc, 'tipo') and doc.tipo else 'Documento'),
                            'archivo': archivo,
                            'origen': origen,
                            'despacho_id': rec.id,
                        })

    def action_generar_legajo_pdf(self):
        """Generar un PDF unificado con todos los documentos del legajo"""
        self.ensure_one()
        documentos = self.documentos_legajo.sorted(key=lambda d: (d.sequence, d.origen))
        merger = PdfMerger()

        for doc in documentos:
            if doc.archivo:
                try:
                    pdf_data = base64.b64decode(doc.archivo)
                    merger.append(io.BytesIO(pdf_data))
                except Exception as e:
                    _logger.error(f"Error al procesar el PDF del documento '{doc.name}': {str(e)}")

        output_stream = io.BytesIO()
        merger.write(output_stream)
        merger.close()
        output_stream.seek(0)

        nombre_archivo = f"legajo_OT_{self.ot}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': nombre_archivo,
            'type': 'binary',
            'datas': base64.b64encode(output_stream.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_generar_pdf_unificado(self):
        self.ensure_one()
        documentos = self.documentos_unificados.sorted(key=lambda d: d.sequence)
        merger = PdfMerger()

        for doc in documentos:
            if doc.archivo:
                try:
                    pdf_data = base64.b64decode(doc.archivo)
                    merger.append(io.BytesIO(pdf_data))
                except Exception as e:
                    _logger.error(f"Error al procesar el PDF del documento '{doc.name}': {str(e)}")

        output_stream = io.BytesIO()
        merger.write(output_stream)
        merger.close()
        output_stream.seek(0)

        nombre_archivo = f"documentos_OT_{self.ot}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': nombre_archivo,
            'type': 'binary',
            'datas': base64.b64encode(output_stream.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    # VALIDACIONES Y ONCHANGE
    @api.onchange('tc')
    def _onchange_tc_bloqueo_manual(self):
        for rec in self:
            if not rec.documento and rec.tc > 0.0:
                rec.tc = 0.0
                return {
                    'warning': {
                        'title': "Advertencia",
                        'message': "Debe subir el documento antes de ingresar el T/C.",
                    }
                }

    @api.constrains('documento', 'tc')
    def _check_tc_vs_documento(self):
        for rec in self:
            if not rec.documento and rec.tc > 0.0:
                raise ValidationError("No puede ingresar el T/C sin haber cargado el documento.")
            if rec.documento and (rec.tc is None or rec.tc <= 0.0):
                raise ValidationError("Debe completar el campo T/C con un valor mayor a cero luego de cargar el documento.")

    @api.onchange('moneda')
    def _compute_tc(self):
        for record in self:
            record.tc = 0.0
            if not record.moneda:
                continue
                
            try:
                url = "https://www.aduana.gov.py/proc.php"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for index, td in enumerate(soup.findAll('td')):
                        if record.moneda.name == 'DOL' and td.text.strip() == 'DOLAR ESTADOUNIDENSE':
                            record.tc = float(
                                soup.findAll('td')[index + 1].text.strip().replace('.', '').replace(',', '.'))
                        elif record.moneda.name == 'MCM' and td.text.strip() == 'MONEDA COMUN EUROPEA':
                            record.tc = float(
                                soup.findAll('td')[index + 1].text.strip().replace('.', '').replace(',', '.'))
            except Exception as e:
                _logger.error(f"Error al obtener tipo de cambio: {str(e)}")

    def _inverse_tc(self):
        pass

    @api.onchange('regimen')
    def regimen_onchange(self):
        for record in self:
            documentos_lines = [(5, 0, 0)]
            if not record.regimen:
                record.documentos = documentos_lines
                continue
                
            tipos_documentos = self.env['despacho.tipo_documento'].search([('regimen', '!=', False)])

            for tipo in tipos_documentos:
                if record.regimen in tipo.regimen:
                    documentos_lines.append((0, 0, {'tipo': tipo.id}))

            record.documentos = documentos_lines

    @api.onchange('fecha_oficializacion', 'oficial')
    def _compute_oficializacion(self):
        for record in self:
            if record.state != 'liquidado' and record.fecha_oficializacion and record.oficial:
                record.state = 'oficializado'

    # MÉTODOS DE ESTADO
    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

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

    # MÉTODOS CRUD
    @api.model
    def create(self, vals):
        if vals.get('ot', _('New')) == _('New') and vals.get('propietario'):
            partner = self.env['res.partner'].browse(vals['propietario'])
            if not partner.exists():
                raise ValidationError("Propietario no válido.")

            prefijo = (partner.codigo or '').strip().upper()
            if not prefijo:
                raise ValidationError("El propietario no tiene un código asignado.")

            _logger.info(f"[OT-GEN] Prefijo: {prefijo}")

            MAX_ATTEMPTS = 5
            BASE_NUMBER = 7011
            attempt = 0

            while attempt < MAX_ATTEMPTS:
                try:
                    all_ots = self.search_read([], ['ot'], order='ot desc')

                    max_num = BASE_NUMBER - 1
                    for ot in all_ots:
                        try:
                            num_str = ''.join(filter(str.isdigit, ot['ot'][-6:]))
                            current_num = int(num_str) if num_str else 0
                            max_num = max(max_num, current_num)
                        except:
                            continue

                    next_num = max_num + 1

                    existing_ot = self.search([('ot', '=', f"{prefijo}{next_num:04d}")], limit=1)
                    if not existing_ot:
                        vals['ot'] = f"{prefijo}{next_num:04d}"
                        _logger.info(f"[OT-GEN] OT generada: {vals['ot']}")
                        return super().create(vals)

                    attempt += 1
                    _logger.warning(f"Intento {attempt}: Número {next_num} ya existe. Reintentando...")

                except Exception as e:
                    attempt += 1
                    _logger.error(f"Error en intento {attempt}: {str(e)}")
                    if attempt >= MAX_ATTEMPTS:
                        raise ValidationError(
                            "No se pudo generar el número de OT después de varios intentos. "
                            "Por favor intente nuevamente o contacte al administrador."
                        )
                    time.sleep(0.5)

            raise ValidationError("No se pudo generar un número único para la OT. Intente nuevamente.")

        return super().create(vals)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        return res

    # MÉTODOS DE ACCIÓN
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

    tipo = fields.Many2one('despacho.tipo_documento', string='Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    archivo = fields.Binary('Archivo', attachment=True)
    original = fields.Boolean('Original')
    visado = fields.Boolean('Visado')
    fecha = fields.Date('Fecha')
    despacho = fields.Many2one('despacho.despacho', 'Despacho', ondelete='cascade')
    monto = fields.Float('Monto')
    imputar = fields.Boolean('Imputar')
    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    def name_get(self):
        result = []
        for record in self:
            if record.numero and record.tipo:
                name = f"{record.tipo.name} - {record.numero}"
            elif record.tipo:
                name = record.tipo.name
            else:
                name = record.numero or 'Documento'
            result.append((record.id, name))
        return result

    def action_crear_factura_proveedor(self):
        for rec in self:
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }

            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
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

    numero_orden = fields.Integer('N° Orden', store=True)
    tipo = fields.Many2one('despacho.tipo_documento_previo', 'Tipo', ondelete='cascade')
    numero = fields.Char('Número')
    archivo = fields.Binary('Archivo', attachment=True)
    fecha = fields.Date('Fecha', compute='_compute_factura_data', store=True)
    vencimiento = fields.Date('Vencimiento')
    despacho = fields.Many2one('despacho.despacho', 'Despacho')
    monto = fields.Float('Monto', compute='_compute_factura_data', store=True)
    pagado_cliente = fields.Float('Pagado por cliente', store=True)
    pagado_por = fields.Selection([
        ('cliente', 'Cliente'),
        ('agencia', 'Agencia')
    ])
    op = fields.Many2one('despacho.ordenpago', 'Orden de pago')
    hr_expense = fields.Many2one('hr.expense', 'Gasto')
    imputar = fields.Boolean('Imputar')
    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    @api.depends('factura_proveedor_id.invoice_date', 'factura_proveedor_id.amount_total')
    def _compute_factura_data(self):
        for rec in self:
            if rec.factura_proveedor_id:
                rec.fecha = rec.factura_proveedor_id.invoice_date
                rec.monto = rec.factura_proveedor_id.amount_total
            else:
                rec.fecha = False
                rec.monto = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.factura_proveedor_id:
                record.fecha = record.factura_proveedor_id.invoice_date
                record.monto = record.factura_proveedor_id.amount_total

            if record.monto > 0:
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': record.monto,
                    'fecha': fields.Date.today(),
                    'vencimiento': record.vencimiento or fields.Date.today()
                })
        return records

    def write(self, vals):
        res = super().write(vals)

        for record in self:
            if 'factura_proveedor_id' in vals and record.factura_proveedor_id:
                record.fecha = record.factura_proveedor_id.invoice_date
                record.monto = record.factura_proveedor_id.amount_total

            if 'monto' in vals and vals['monto'] > 0:
                if record.op:
                    record.op.unlink()
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': vals['monto'],
                    'fecha': fields.Date.today(),
                    'vencimiento': vals.get('vencimiento', record.vencimiento) or fields.Date.today()
                })

        return res

    def action_crear_factura_proveedor(self):
        for rec in self:
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }

            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
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

    vencimiento = fields.Date('Vencimiento')
    tipo = fields.Many2one('despacho.tipo_documento_oficializacion', 'Tipo', ondelete='restrict')
    numero = fields.Char('Número')
    archivo = fields.Binary('Documento', attachment=True)
    fecha = fields.Date('Fecha', compute='_compute_factura_data', store=True)
    monto = fields.Float('Monto', compute='_compute_factura_data', store=True)
    pagado_por = fields.Selection([
        ('cliente', 'Cliente'),
        ('agencia', 'Agencia')
    ])
    despacho = fields.Many2one('despacho.despacho', 'Despacho')
    op = fields.Many2one('despacho.ordenpago', 'Orden de pago')
    hr_expense = fields.Many2one('hr.expense', 'Gasto')
    imputar = fields.Boolean('Imputar')
    factura_proveedor_id = fields.Many2one('account.move', string='Factura')

    @api.depends('factura_proveedor_id.invoice_date', 'factura_proveedor_id.amount_total')
    def _compute_factura_data(self):
        for rec in self:
            if rec.factura_proveedor_id:
                rec.fecha = rec.factura_proveedor_id.invoice_date
                rec.monto = rec.factura_proveedor_id.amount_total
            else:
                rec.fecha = False
                rec.monto = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.factura_proveedor_id:
                record.fecha = record.factura_proveedor_id.invoice_date
                record.monto = record.factura_proveedor_id.amount_total

            if record.monto > 0:
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': record.monto,
                    'fecha': fields.Date.today(),
                    'vencimiento': record.vencimiento or fields.Date.today()
                })
        return records

    def write(self, vals):
        res = super().write(vals)

        for record in self:
            if 'factura_proveedor_id' in vals and record.factura_proveedor_id:
                record.fecha = record.factura_proveedor_id.invoice_date
                record.monto = record.factura_proveedor_id.amount_total

            if 'monto' in vals and vals['monto'] > 0:
                if record.op:
                    record.op.unlink()
                record.op = self.env['despacho.ordenpago'].create({
                    'despacho': record.despacho.id,
                    'monto': vals['monto'],
                    'fecha': fields.Date.today(),
                    'vencimiento': vals.get('vencimiento', record.vencimiento) or fields.Date.today()
                })

        return res

    def action_crear_factura_proveedor(self):
        for rec in self:
            if rec.factura_proveedor_id:
                return {
                    'name': 'Factura Proveedor',
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'res_id': rec.factura_proveedor_id.id,
                }

            factura = self.env['account.move'].create({
                'partner_id': rec.despacho.propietario.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': rec.despacho.ot,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Factura proveedor desde Documento',
                    'quantity': 1,
                    'price_unit': 100,
                    'account_id': self.env['account.account'].search([('account_type', '=', 'expense')], limit=1).id,
                })],
            })

            rec.write({
                'numero': factura.name,
                'factura_proveedor_id': factura.id,
            })

            return {
                'name': 'Factura Proveedor',
                'view_mode': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': factura.id,
            }


class DocumentoUnificado(models.Model):
    _name = 'despacho.documento_unificado'
    _description = 'Documento Unificado para OT'
    _order = 'sequence'

    name = fields.Char('Nombre')
    archivo = fields.Binary('Archivo', attachment=True, required=True)
    despacho_id = fields.Many2one('despacho.despacho', string='Orden de Trabajo', ondelete='cascade')
    sequence = fields.Integer(string="Orden", default=10)
    origen = fields.Selection([
        ('gabinete', 'Gabinete'),
        ('datos', 'Datos'),
        ('oficializacion', 'Oficialización'),
        ('documentos', 'Documentos'),
    ], string='Origen')


class DocumentoLegajo(models.Model):
    _name = 'despacho.documento_legajo'
    _description = 'Documento para Legajo de Despacho'
    _order = 'sequence'

    name = fields.Char('Nombre', required=True)
    archivo = fields.Binary('Archivo', attachment=True, required=True)
    despacho_id = fields.Many2one('despacho.despacho', string='Orden de Trabajo', ondelete='cascade')
    sequence = fields.Integer(string="Orden", default=10)
    origen = fields.Selection([
        ('gabinete', 'Gabinete'),
        ('datos', 'Datos'),
        ('oficializacion', 'Oficialización'),
        ('presupuesto', 'Presupuesto'),
        ('manual', 'Manual'),
        ('liquidacion', 'Liquidación'),
    ], string='Origen', default='manual')

    tipo_documento = fields.Char('Tipo de Documento')
    monto = fields.Float('Monto')
    fecha_documento = fields.Date('Fecha del Documento')
    observaciones = fields.Text('Observaciones')
    responsable = fields.Many2one(
        'hr.employee',
        string='Responsable',
        default=lambda self: self.env.user.employee_id
    )

    # Campos para sincronización con documentos originales
    documento_origen_id = fields.Integer('ID Documento Origen')
    modelo_origen = fields.Char('Modelo Origen')
    imputado = fields.Boolean('Imputado')

    # Campo para facturas relacionadas
    factura_id = fields.Many2one('account.move', string='Factura Relacionada')
    numero_factura = fields.Char('Número de Factura', related='factura_id.name', store=True)
    fecha_factura = fields.Date('Fecha Factura', related='factura_id.invoice_date', store=True)
    monto_factura = fields.Monetary('Monto Factura', related='factura_id.amount_total', store=True)
    currency_id = fields.Many2one('res.currency', related='factura_id.currency_id', string='Moneda')

    def name_get(self):
        result = []
        for record in self:
            if record.tipo_documento and record.name:
                name = f"{record.tipo_documento} - {record.name}"
            elif record.name:
                name = record.name
            else:
                name = 'Documento'
            result.append((record.id, name))
        return result

    @api.onchange('imputado')
    def _onchange_imputado(self):
        """Sincroniza el campo imputado con el documento original"""
        for rec in self:
            if rec.documento_origen_id and rec.modelo_origen:
                try:
                    modelo = self.env[rec.modelo_origen]
                    documento_origen = modelo.browse(rec.documento_origen_id)
                    if documento_origen and hasattr(documento_origen, 'imputar'):
                        documento_origen.sudo().write({'imputar': rec.imputado})
                except Exception as e:
                    _logger.error(f"Error al sincronizar imputado: {str(e)}")

    def write(self, vals):
        """Sincroniza el campo imputado cuando se edita directamente"""
        res = super().write(vals)
        if 'imputado' in vals:
            for rec in self:
                rec._onchange_imputado()
        return res