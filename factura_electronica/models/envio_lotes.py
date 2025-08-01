from odoo import fields, models, api
import json
import logging
from io import BytesIO
import zipfile
import base64
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import lxml.etree
from signxml import XMLSigner, XMLVerifier
import signxml
from odoo.tools import float_compare, float_round, float_is_zero
from hashlib import md5,sha256,sha224
from odoo.exceptions import ValidationError
import pytz
ROUNDING=1
import urllib3
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL:@SECLEVEL=1'


_logger = logging.getLogger(__name__)

class EnvioLotes(models.Model):
    _name = 'envio.lotes'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"
    _description = 'Envio de Lotes DE'



    

    name=fields.Char( copy=False, readonly=True, default=lambda x: 'Nuevo')


    tipo=fields.Selection(selection=[('1', 'Factura electrónica'),
                           ('2', 'Factura electrónica de exportación'),
                           ('3', 'Factura electrónica de importación'),
                           ('4', 'Autofactura electrónica'),
                           ('5', 'Nota de crédito electrónica'),
                           ('6', 'Nota de débito electrónica'),
                           ('7', 'Nota de remisión electrónica'),
                           ('8', 'Comprobante de retención electrónico')
                           ],string="Tipo Documento Electronico")


    invoice_ids=fields.Many2many('account.move','account_move_lote_rel','lote_id','move_id','Facturas')
    state=fields.Selection(selection=[('borrador','Borrador'),('enviado','Enviado'),('cerrado','Cerrado')],string="Estado",default='borrador', tracking=True)
    numero_lote=fields.Integer(copy=False)
    domain_tipo=fields.Char(compute='_domain_tipo')
    archivo=fields.Binary(copy=False)
    fecha_envio=fields.Datetime(tracking=True)
    # campos de respuesta de parte de la set
    dMsgRes = fields.Char(string="Mje de Respuesta",copy=False)
    dCodRes = fields.Char(string='Codigo de respuesta',copy=False)
    dFecProc = fields.Datetime(string='Fecha de Respuesta',copy=False)
    dProtConsLote = fields.Char(string='Nro Lote de Resp.',copy=False)
    dTpoProces = fields.Datetime(string='Tiempo medio de Procesamiento ms',copy=False)

    # campos para respuesta de consulta del lote
    con_dMsgRes = fields.Char(string="Mje de Respuesta de Consulta",copy=False)
    con_dCodRes = fields.Char(string='Codigo de respuesta de la Consulta',copy=False)
    con_dFecProc = fields.Datetime(string='Fecha de Respuesta de la Consulta',copy=False)
    respuesta = fields.Text(copy=False)


    @api.model
    def create(self,vals):
        res = super(EnvioLotes, self).create(vals)
        for r in res:
            nombre=self.env['ir.sequence'].next_by_code('envio.lote.name.sequence')
            r.name = nombre
            nro=nombre.split('/')
            if nro:
                try:
                    numero=int(nro[2])
                except:
                    numero=None
            r.numero_lote = numero
        return res


    @api.depends('tipo')
    def _domain_tipo(self):
        self.domain_tipo = False
        if len(self)==1:
            ids=[]
            if self.tipo:
                invoices=self.env['account.move'].search([('talonario_factura.timbrado_electronico','=',self.tipo),('company_id','=',self.env.company.id),('estado_de','in',('no-enviado','rechazado','enviado')),
                                                          ('state','=','posted')])
                ids = [ l.id for l in invoices]
                self.domain_tipo = json.dumps([('id', 'in', ids)])


    def crear_zip(self):
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        self.generar_xml(certificado)


    def generar_xml(self,certificado):


        rLoteDE = lxml.etree.Element('rLoteDE')


        for inv in self.invoice_ids:
            xml = inv.generar_xml(certificado,True)
            inv.generate_qr_code()
            xml = str(xml)[2:-1]
            lxml.etree.SubElement(rLoteDE, 'sati').text = xml

        data_serialized = lxml.etree.tostring(rLoteDE)
        data=str(data_serialized)[2:-1]
        # data=data.replace('<sati>',"").replace("</sati>","").replace('&gt;','>').replace('&lt;','<').replace('&amp;','&')
        data=data.replace('<sati>',"").replace("</sati>","").replace('&gt;','>').replace('&lt;','<').replace('&amp;','&')
        data=reemplazar_acentos(data)
        data_serialized=data.encode(encoding="ascii",errors="xmlcharrefreplace")


        file_name = 'Lote-' + str(self.numero_lote) + '.xml'
        files = []
        files.append((file_name, data_serialized))
        full_zip_in_memory = generate_zip(files)
        archivo = base64.b64encode(full_zip_in_memory)
        self.archivo = archivo




    def enviar(self):
        if not self.archivo:
            raise ValidationError('Debe generar primero el archivo ZIP para enviar')

        if self.env.company.servidor == 'prueba':
            wsdl = 'https://sifen-test.set.gov.py/de/ws/async/recibe-lote.wsdl'
        else:
            wsdl = 'https://sifen.set.gov.py/de/ws/async/recibe-lote.wsdl'
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        soap = self.generar_soap_RecepLoteDE()
        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        certificado2 = (public_crt, private_key)
        try:

            response = requests.post(url=wsdl, data=soap, cert=certificado2, headers=headers, verify=False, timeout=180)


            code_300=self.parsear_response(response)

            if code_300:
                self.fecha_envio=datetime.now()
                for inv in self.invoice_ids:
                    inv.estado_de='enviado'
            return code_300
        except:

                raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde %s' % response.text)

    def generar_soap_RecepLoteDE(self):
        header = '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns0="http://ekuatia.set.gov.py/sifen/xsd">' \
                 '<soap:Body>' \
                 '<ns0:rEnvioLote>'
        id = '<ns0:dId>' + str(self.numero_lote) + '</ns0:dId>'
        archivo=str(self.archivo)
        archivo=archivo[2:-1]
        rde = '<ns0:xDE>' + archivo + '</ns0:xDE>'
        footer = '</ns0:rEnvioLote>' \
                 '</soap:Body>' \
                 '</soap:Envelope>'
        soap = header + id + rde + footer
        # _logger.info('------soap-------')
        # _logger.info(soap)
        # _logger.info('------fin soap------')
        return soap

    def parsear_response(self,response):
        # _logger.info('Codigo de retorno set %s' %response.status_code)
        # _logger.info('respueta set %s' %response.text)
        code_300 = False
        if response.status_code ==200:
            res_tex = response.text
            if res_tex.find('html')<0:
                self.respuesta = res_tex
                res_tex = res_tex.replace('env:', "").replace('ns2:', "")
                rResEnviLoteDe = res_tex[res_tex.find('rResEnviLoteDe') - 1:res_tex.rfind('rResEnviLoteDe') + len('rResEnviLoteDe') + 1]
                root = ET.fromstring(rResEnviLoteDe)

                for child in root:
                    if child.tag=='dFecProc':
                        dFecProc=child.text
                        dFecProc=dFecProc[:dFecProc.rfind('-')]
                        date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S')
                        self.dFecProc=date_time_obj
                    elif child.tag=='dMsgRes':
                        self.dMsgRes=child.text
                    elif child.tag=='dProtConsLote':
                        self.dProtConsLote=child.text
                    elif child.tag=='dCodRes':
                        self.dCodRes=child.text
                        if child.text=='0300':
                            code_300=True
                if code_300:
                    self.state='enviado'
            else:
                raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde %s' % response)
        return code_300


    def consultar_estado(self):
        if self.env.company.servidor == 'prueba':
            wsdl = 'https://sifen-test.set.gov.py/de/ws/consultas/consulta-lote.wsdl'
        else:
            wsdl = 'https://sifen.set.gov.py/de/ws/consultas/consulta-lote.wsdl'
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        soap = self.generar_soap_consulta()
        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        certificado2 = (public_crt, private_key)

        response = requests.post(url=wsdl, data=soap, cert=certificado2, headers=headers, verify=False, timeout=60)
        self.parsear_response_consulta(response)

    def parsear_response_consulta(self, response):
            # _logger.info('Codigo de retorno set %s' % response.status_code)
            # _logger.info('respueta set %s' % response.text)
            code_362 = False
            if self.tipo != '7':
                if response.status_code == 200:
                    res_tex = response.text
                    if res_tex.find('html') < 0:
                        self.respuesta = res_tex
                        res_tex = res_tex.replace('env:', "").replace('ns2:', "")
                        rResEnviConsLoteDe = res_tex[res_tex.find('rResEnviConsLoteDe') - 1:res_tex.rfind('rResEnviConsLoteDe') + len(
                            'rResEnviConsLoteDe') + 1]
                        root = ET.fromstring(rResEnviConsLoteDe)
                        for child in root:
                            if child.tag == 'dFecProc':
                                dFecProc = child.text
                                # dFecProc = dFecProc[:dFecProc.rfind('-')]
                                # date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S')
                                date_time_obj = parsear_fecha_respuesta(dFecProc)

                                self.con_dFecProc = date_time_obj
                            elif child.tag == 'dMsgResLot':
                                self.con_dMsgRes = child.text
                            elif child.tag == 'dCodResLot':
                                self.con_dCodRes = child.text
                                if child.text == '0362':
                                    code_362 = True
                            elif child.tag == 'gResProcLote':
                                data={}
                                for c in child:
                                    if c.tag == 'id':
                                        invoice = self.env['account.move'].search([('cdc', '=', c.text)])
                                        data = {'invoice_id': invoice.id}
                                    elif c.tag == 'dEstRes':
                                        if c.text =="Rechazado":
                                            invoice.estado_de='rechazado'
                                        if c.text =="Aprobado" or c.text=="Aprobado con observación":
                                            invoice.estado_de='aprobado'
                                    elif c.tag=="gResProc":
                                        for c2 in c:
                                            if c2.tag == 'dCodRes':
                                                data.update({'name': '0362-'+c2.text})
                                                if c2.text == '1001': #EN CASO QUE EL CDC DEL DE YA SE ENCUENTRA EN EL SIFEN, NO SE DEBE PASAR A RECHAZADO, AQUI FORZAMOS QUE SE MANTENGA COMO APROBADO EN ESE CASO
                                                    invoice.estado_de='aprobado'
                                            elif c2.tag == 'dMsgRes':
                                                # _logger.info('dMsgRes tag %s' %str(c2.tag))
                                                # _logger.info('dMsgRes data %s' %str(c2.text))
                                                dato_string=c2.text
                                                data.update({'dMsgRes': dato_string,'tipo':'lote'})

                                if data:
                                    self.env['mje.resultado'].create(data)
                        if code_362:
                            self.state = 'cerrado'
                    else:
                        raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde')



    def generar_soap_consulta(self):
        header = '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns0="http://ekuatia.set.gov.py/sifen/xsd">' \
                 '<soap:Body>' \
                 '<ns0:rEnviConsLoteDe>'
        id = '<ns0:dId>' + str(self.id) + '</ns0:dId>'
        dProtConsLote = '<ns0:dProtConsLote>' + str(self.dProtConsLote) + '</ns0:dProtConsLote>'
        footer = '</ns0:rEnviConsLoteDe>' \
                 '</soap:Body>' \
                 '</soap:Envelope>'
        soap = header + id + dProtConsLote + footer
        # _logger.info('------soap-------')
        # _logger.info(soap)
        # _logger.info('------fin soap------')
        return soap











def generate_zip(files):
    mem_zip = BytesIO()

    with zipfile.ZipFile(mem_zip, mode="w",compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.writestr(f[0], f[1])

    return mem_zip.getvalue()

def reemplazar_acentos(string):

    string=string.replace('&amp;#225;','á').replace('&amp;#233;','é').replace('&amp;#237;','í').replace('&amp;#243;','ó').replace('&amp;#250;','ú')
    string=string.replace('&amp;#193;;','Á').replace('&amp;#201;','É').replace('&amp;#205;','Í').replace('&amp;#211;','Ó').replace('&amp;#218;','Ú')
    string=string.replace('&amp;#241;','ñ').replace('&amp;#209;','Ñ')
    return string

def parsear_fecha_respuesta(fecha):
    dFecProc = fecha[:fecha.rfind('-')]
    tz_string = fecha[fecha.rfind('-'):]
    tz_string = tz_string.replace(':', '')
    dFecProc = dFecProc + tz_string
    # _logger.info(dFecProc)
    date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S%z')
    date_time = date_time_obj.astimezone(pytz.utc).replace(tzinfo=None)
    return date_time
