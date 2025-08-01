import os
from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
import pytz
from datetime import datetime
from dateutil import parser
import collections
import requests
requests.packages.urllib3.disable_warnings()
import base64
from requests import Session
import lxml.etree
from signxml import XMLSigner, XMLVerifier, InvalidInput
import signxml
from odoo import http, _
from odoo.http import request
import operator
from collections import OrderedDict
import logging
_logger = logging.getLogger(__name__)



class EventosDte(models.Model):
    _name = 'eventos.dte'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    tipo_comprobante = fields.Selection(selection=[('1', 'Factura electrónica'),
                                       ('2', 'Factura electrónica de exportación'),
                                       ('3', 'Factura electrónica de importación'),
                                       ('4', 'Autofactura electrónica'),
                                       ('5', 'Nota de crédito electrónica'),
                                       ('6', 'Nota de débito electrónica'),
                                       ('7', 'Nota de remisión electrónica'),
                                       ('8', 'Comprobante de retención electrónico'),
                                       ('9', 'No definido')
                                       ], string="Tipo Comprobante")
# ,compute="set_comprobante"
    name=fields.Char( copy=False, readonly=True, default=lambda x: 'Nuevo')
    tipo=fields.Selection(selection=[('cancelacion' , 'Cancelacion'),
                                    ('inutilizacion' , 'Inutilizacion'),
                                    ('recepcion' , 'Recepción DE/DTE'),
                                    ('conformidad' , 'Conformidad'),
                                    ('disconformidad' , 'Disconformidad'),
                                    ('desconocimiento' , 'Desconocimiento DE/DTE')
                                    ])

    agente=fields.Selection(selection=[('1','emisor'),('2','receptor')])
    invoice_id=fields.Many2one('account.move',string='Documento Electronico')
    timbrado_id=fields.Many2one('ruc.documentos.timbrados')
    state=fields.Selection(selection=[('borrador','Borrador'),('aprobado','Aprobado'),('rechazado','Rechazado')],default='borrador')
    fecha_envio=fields.Datetime()
    fecha_firma=fields.Datetime()
    mOtEve=fields.Char(string='Motivo del Evento')
    cdc=fields.Char(string='CDC')
    respuesta=fields.Char()
    dNumIn=fields.Char(string='Numero de inicio del rango',size=7)
    dNumFin=fields.Char(string='Numero de final del rango',size=7)

    #campos para receptor
    cdc_receptor=fields.Char(size=44)
    dFecEmi=fields.Datetime(string='Fecha de Emision')
    dFecRecep=fields.Datetime(string='Fecha de Recepcion')
    iTipRec=fields.Selection(selection=[('1','Contribuyente'),
                                        ('2','No Contribuyente')],
                             string='Tipo de Receptor',default='1')
    dNomRec=fields.Many2one('res.partner',string='Nombre o Razon Social')
    dRucRec=fields.Char(string='RUC del receptor')
    dDVRec=fields.Char(string='Digito Verificador',size=1)
    # dTipIDRec=fields.Selection(selection=[])
    # dNumID=fields.Char()
    dTotalGs=fields.Float(string='Monto Total en Gs.')

    # campos para conformidad
    iTipConf=fields.Selection(selection=[('1','Conformidad Total del DTE'),
                                         ('2','Conformidad Parcial del DTE')],
                              string='Tipo de Conformidad')
    dFecRecep=fields.Datetime(string='Fecha Estimada de Recepcion')

    # campos de respuestas
    dFecProc=fields.Datetime(string='Fecha de Respuesta')
    dMsgRes=fields.Char(string='Mensaje de Respuesta')
    dCodRes=fields.Char(string='Codigo de Respuesta')
    dEstRes=fields.Char(string='Estado de Respuesta')
    dProtAut=fields.Char(string='Codigo de operacion')

    @api.depends('cdc','tipo')
    def set_comprobante(self):
        for rec in self:
            if rec.tipo and rec.tipo == 'cancelacion':
                if rec.cdc:
                    cadena = str(rec.cdc)
                    # print(f"cadena[:2]->> {cadena[:2]}")
                    if cadena[:2] == '01':
                        rec.tipo_comprobante = '1'
                    elif cadena[:2] == '07':
                        rec.tipo_comprobante = '7'
                    else:
                        rec.tipo_comprobante = '9'

    def descargar_xml(self):

        return {
            'type': 'ir.actions.act_url',
            'url': '/getXMLEventoDTE/' + str(self.id),
            'target': 'current'
        }

    class DownloadXML(http.Controller):
        @http.route('/getXMLEventoDTE/<int:id>', auth='public', type='http')
        def descargaXML(self, id=None, **kw):
            record = request.env['eventos.dte'].browse(id)
            certificado = request.env['firma.digital'].search([
                ('company_id', '=', record.env.user.company_id.id),
                ('estado', '=', 'activo')
            ], limit=1)

            xml = record.generar_xml(certificado)
            xml = str(xml)[2:-1]
            soap = record.generar_soap_eventos_dte(xml)
            xml2 = soap
            characters = "\\n"
            xml2 = xml2.replace(characters, "")
            
            
            filename = 'eventoDTE-' + str(record.id) + '.xml'
            return request.make_response(xml2,
                                         [('Content-Type',
                                           'application/xml'),
                                          ('Content-Disposition', content_disposition(filename))])

    @api.model
    def create(self, vals):
        res = super(EventosDte, self).create(vals)
        for r in res:
            r.name = self.env['ir.sequence'].get('eventos.sequence')
        return res

    @api.onchange('dNomRec')
    def setear_ruc_dv(self):
        self.dRucRec=''
        self.dDVRec=''
        if self.dNomRec:
            self.dRucRec = self.dNomRec.ruc
            self.dDVRec = self.dNomRec.dv



    @api.onchange('tipo')
    def setear_agente(self):
        if self.tipo:
            if self.tipo in ('cancelacion','inutilizacion'):
                self.agente='1'
            else:
                self.agente='2'
        else:
            self.agente=False


    @api.onchange('invoice_id')
    def setear_cdc(self):
        self.cdc=None
        if self.invoice_id:
            if self.invoice_id.cdc:
                self.cdc=self.invoice_id.cdc

    def enviar(self):
        _logger.info('1111')
        if self.env.company.servidor == 'prueba':
            wsdl = 'https://sifen-test.set.gov.py/de/ws/eventos/evento.wsdl'
        else:
            wsdl = 'https://sifen.set.gov.py/de/ws/eventos/evento.wsdl'
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        _logger.info('2222')
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        _logger.info('33333')
        xml = self.generar_xml(certificado)
        _logger.info('44444')

        _logger.info(str(xml))
        xml = str(xml)[2:-1]



        soap = self.generar_soap_eventos_dte(xml)
        characters = "\\n"
        # xml2=soap
        # xml2 = xml2.replace(characters, "")
        soap= soap.replace(characters, "")
        # _logger.info('--------soap-----')
        # _logger.info(xml2)
        # for certi in soap.iter('X509Certificate'):
        # raise ValidationError('test %s' % xml2)

        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        certificado2 = (public_crt, private_key)
        # _logger.info('pre envio wsdl %s'% wsdl)
        # _logger.info('pre envio soap %s'% soap)
        # _logger.info('pre envio headers %s'% headers)
        response = requests.post(url=wsdl, data=soap, cert=certificado2, headers=headers, verify=False, timeout=180)
        self.parsear_response(response)

        self.fecha_envio=datetime.now()
        if self.tipo == 'cancelacion' and self.state =='aprobado':
            self.invoice_id.estado_de='cancelado'



    def generar_xml(self,certificado):



        NAMESPACE = {
            None: 'http://ekuatia.set.gov.py/sifen/xsd',
            # 'ns2':'http://www.w3.org/2000/09/xmldsig#',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }
        attr_qname = lxml.etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")


        rGesEve = lxml.etree.Element('rGesEve',{attr_qname: 'http://ekuatia.set.gov.py/sifen/xsd siRecepEvento_v150.xsd'},
                                           nsmap=NAMESPACE)
        rEve = lxml.etree.SubElement( rGesEve,'rEve', Id=str(self.id))
        self.fecha_firma = datetime.now()
        fecha_firma=formatear_fecha(self.fecha_firma)
        lxml.etree.SubElement(rEve, 'dFecFirma').text = str(fecha_firma)
        lxml.etree.SubElement(rEve,'dVerFor').text = '150'
        gGroupTiEvt=lxml.etree.SubElement(rEve, 'gGroupTiEvt')
        if self.tipo == 'cancelacion':
            rGeVeCan=lxml.etree.SubElement(gGroupTiEvt, 'rGeVeCan')
            if not self.cdc:
                raise ValidationError('Se necesita el cdc para este evento')
            lxml.etree.SubElement(rGeVeCan, 'Id').text = str(self.cdc)
            if len(self.mOtEve)<5:
                raise ValidationError('El campo de motivo de evento debe ser mayor a 5 caracteres')
            lxml.etree.SubElement(rGeVeCan, 'mOtEve').text = str(self.mOtEve)
        elif self.tipo == 'inutilizacion':
            rGeVeInu = lxml.etree.SubElement(gGroupTiEvt, 'rGeVeInu')

            lxml.etree.SubElement(rGeVeInu, 'dNumTim').text = str(self.timbrado_id.name)
            dEst=self.timbrado_id.suc
            if len(dEst) != 3:
                for i in range(len(dEst),3):
                    dEst='0'+dEst
            lxml.etree.SubElement(rGeVeInu, 'dEst').text = str(dEst)
            dPunExp=self.timbrado_id.sec
            if len(dPunExp) != 3:
                for i in range(len(dPunExp),3):
                    dPunExp='0'+dPunExp
            lxml.etree.SubElement(rGeVeInu, 'dPunExp').text = str(dPunExp)
            dNumIn=self.dNumIn
            if len(dNumIn) != 7:
                for i in range(len(dNumIn), 7):
                    dNumIn = '0' + dNumIn
            lxml.etree.SubElement(rGeVeInu, 'dNumIn').text = str(dNumIn)
            dNumFin=self.dNumFin
            if len(dNumFin) != 7:
                for i in range(len(dNumFin), 7):
                    dNumFin = '0' + dNumFin
            lxml.etree.SubElement(rGeVeInu, 'dNumFin').text = str(dNumFin)
            iTiDE = self.timbrado_id.timbrado_electronico
            lxml.etree.SubElement(rGeVeInu, 'iTiDE').text = str(iTiDE)
            if len(self.mOtEve)<5:
                raise ValidationError('El campo de motivo de evento debe ser mayor a 5 caracteres')
            lxml.etree.SubElement(rGeVeInu, 'mOtEve').text = str(self.mOtEve)
        elif self.tipo =='recepcion':
            rGeVeNotRec = lxml.etree.SubElement(gGroupTiEvt, 'rGeVeNotRec')
            lxml.etree.SubElement(rGeVeNotRec, 'Id').text = str(self.cdc_receptor)
            dFecEmi=formatear_fecha(self.dFecEmi)
            lxml.etree.SubElement(rGeVeNotRec, 'dFecEmi').text = str(dFecEmi)
            dFecRecep=formatear_fecha((self.dFecRecep))
            lxml.etree.SubElement(rGeVeNotRec, 'dFecRecep').text = str(dFecRecep)
            lxml.etree.SubElement(rGeVeNotRec, 'iTipRec').text = str(self.iTipRec)
            lxml.etree.SubElement(rGeVeNotRec, 'dNomRec').text = str(self.dNomRec.name)
            lxml.etree.SubElement(rGeVeNotRec, 'dRucRec').text = str(self.dRucRec)
            lxml.etree.SubElement(rGeVeNotRec, 'dDVRec').text = str(self.dDVRec)
            lxml.etree.SubElement(rGeVeNotRec, 'dTotalGs').text = str(self.dTotalGs)
        elif self.tipo == 'conformidad':
            rGeVeConf = lxml.etree.SubElement(gGroupTiEvt, 'rGeVeConf')
            lxml.etree.SubElement(rGeVeConf, 'Id').text = str(self.cdc_receptor)
            lxml.etree.SubElement(rGeVeConf, 'iTipConf').text = str(self.iTipConf)
            if self.iTipConf ==1:
                dFecRecep=formatear_fecha(self.dFecRecep)
                lxml.etree.SubElement(rGeVeConf, 'dFecRecep').text = str(dFecRecep)
        elif self.tipo == 'disconformidad':
            rGeVeDisconf = lxml.etree.SubElement(gGroupTiEvt, 'rGeVeDisconf')
            lxml.etree.SubElement(rGeVeDisconf, 'Id').text = str(self.cdc_receptor)
            if len(self.mOtEve) < 5:
                raise ValidationError('El campo de motivo de evento debe ser mayor a 5 caracteres')
            lxml.etree.SubElement(rGeVeDisconf, 'mOtEve').text = str(self.mOtEve)
        elif self.tipo == 'desconocimiento':
            rGeVeDescon = lxml.etree.SubElement(gGroupTiEvt, 'rGeVeDescon')
            lxml.etree.SubElement(rGeVeDescon, 'Id').text = str(self.cdc_receptor)
            dFecEmi = formatear_fecha(self.dFecEmi)
            lxml.etree.SubElement(rGeVeDescon, 'dFecEmi').text = str(dFecEmi)
            dFecRecep = formatear_fecha((self.dFecRecep))
            lxml.etree.SubElement(rGeVeDescon, 'dFecRecep').text = str(dFecRecep)
            lxml.etree.SubElement(rGeVeDescon, 'iTipRec').text = str(self.iTipRec)
            lxml.etree.SubElement(rGeVeDescon, 'dNomRec').text = str(self.dNomRec.name)
            lxml.etree.SubElement(rGeVeDescon, 'dRucRec').text = str(self.dRucRec)
            lxml.etree.SubElement(rGeVeDescon, 'dDVRec').text = str(self.dDVRec)
            if len(self.mOtEve) < 5:
                raise ValidationError('El campo de motivo de evento debe ser mayor a 5 caracteres')
            lxml.etree.SubElement(rGeVeDescon, 'mOtEve').text = str(self.mOtEve)


        key2 = open(certificado.private_key).read()
        cert2 = open(certificado.public_key).read()
        signer = XMLSigner(method=signxml.methods.enveloped,
                                c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
                                signature_algorithm='rsa-sha256', digest_algorithm="sha256")

        ns = {}
        ns[None] = signer.namespaces['ds']
        signer.namespaces = ns
        signed_root=signer.sign(rGesEve,reference_uri="#" + str(self.id),id_attribute="Id",key=key2,cert=cert2)


        #signed_root = signer.sign(rde, reference_uri="#" + str(self.cdc), id_attribute="Id", key=key2, cert=cert2)

        # verifica la firma correcta
        # verified_data=XMLVerifier().verify(signed_root,ca_pem_file=certificado.private_key,x509_cert=cert2).signed_xml
        # _logger.info(verified_data)


        data_serialized = lxml.etree.tostring(signed_root)


        return data_serialized




    def generar_soap_eventos_dte(self,xml):
        header = '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns0="http://ekuatia.set.gov.py/sifen/xsd">' \
                 '<soap:Body>' \
                 '<ns0:rEnviEventoDe>'
        id = '<ns0:dId>' + str(self.id) + '</ns0:dId>'
        rde='<ns0:dEvReg> <gGroupGesEve  xmlns="http://ekuatia.set.gov.py/sifen/xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  xsi:schemaLocation="http://ekuatia.set.gov.py/sifen/xsd siRecepEvento_v150.xsd" >'+xml+'</gGroupGesEve></ns0:dEvReg>'
        # rde='<ns0:dEvReg> '+xml+'</ns0:dEvReg>'
        footer = '</ns0:rEnviEventoDe>' \
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

        self.respuesta = response.text
        if response.status_code ==200:
            res_tex = response.text
            if res_tex.find('html')<0 and res_tex.find('rRetEnviEventoDe')>0:

                res_tex = res_tex.replace('env:', "").replace('ns2:', "")
                rResEnviLoteDe = res_tex[res_tex.find('rRetEnviEventoDe') - 1:res_tex.rfind('rRetEnviEventoDe') + len('rRetEnviEventoDe') + 1]
                root = lxml.etree.fromstring(rResEnviLoteDe)
                estado=''
                for child in root:
                    if child.tag=='dFecProc':
                        fecha=child.text
                        date_time=parsear_fecha_respuesta(fecha)
                        # dFecProc=fecha[:fecha.rfind('-')]
                        # tz_string=fecha[fecha.rfind('-'):]
                        # tz_string=tz_string.replace(':', '')
                        # dFecProc=dFecProc+tz_string
                        # _logger.info(dFecProc)
                        # date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S%z')
                        # date_time = date_time_obj.astimezone(pytz.utc).replace(tzinfo=None)
                        # dd=parser.parse(dFecProc)
                        # _logger.info(type(dd))
                        self.dFecProc=date_time
                    if child.tag == 'gResProcEVe':
                        for c in child:
                            if c.tag=='dProtAut':
                                self.dProtAut=c.text
                            elif c.tag=='dEstRes':
                                estado=c.text
                                self.dEstRes=c.text
                            elif c.tag=='gResProc':
                                for c1 in c:
                                    if c1.tag == 'dMsgRes':
                                        self.dMsgRes = c1.text
                                    elif c1.tag=='dCodRes':
                                        self.dCodRes=c1.text

                if estado == 'Aprobado':
                    self.state='aprobado'
                elif estado =='Rechazado':
                    self.state = 'rechazado'



def formatear_fecha(fecha_firma):
    """
    Funcion donde formatea la fecha segun el Manual tecnico SIFEN
    :param fecha_firma:FECHA Y HORA CON FORMATO ODOO
    :return: FECHA Y HORA CON FORMATO SIFEN
    """
    # _logger.info('Formato odoo : %s' %str(fecha_firma) )
    fecha_firma = str(fecha_firma.isoformat())
    fecha_firma = fecha_firma[:fecha_firma.find('.')]
    date_time_obj = datetime.strptime(fecha_firma, '%Y-%m-%dT%H:%M:%S')
    tz1 = 'America/Asuncion'
    tz = pytz.timezone(tz1)
    fecha = pytz.utc.localize(date_time_obj).astimezone(tz)
    fecha = fecha.isoformat()
    fecha = str(fecha)
    fecha_firma = fecha[:fecha.rfind('-')]
    # _logger.info('Formato sifen: %s' %str(fecha_firma))
    return fecha_firma

def parsear_fecha_respuesta(fecha):
    dFecProc = fecha[:fecha.rfind('-')]
    tz_string = fecha[fecha.rfind('-'):]
    tz_string = tz_string.replace(':', '')
    dFecProc = dFecProc + tz_string
    # _logger.info(dFecProc)
    date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S%z')
    date_time = date_time_obj.astimezone(pytz.utc).replace(tzinfo=None)
    return date_time

