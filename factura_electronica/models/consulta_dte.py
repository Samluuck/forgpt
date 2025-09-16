from odoo import fields, models, api
from odoo.exceptions import ValidationError
import pytz
from datetime import datetime
import collections
import requests
from requests import Session
import lxml.etree
import xml.etree.ElementTree as ET
import logging
from signxml import XMLSigner, XMLVerifier
import signxml
from odoo import http, _
from odoo.http import request
import operator
import base64
_logger = logging.getLogger(__name__)
try:
    from zeep import Client
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
except (ImportError, IOError) as err:
    _logger.debug(err)


class ConsultaDte(models.Model):
    _name = 'consulta.dte'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    @api.model
    def create(self, vals):
        res = super(ConsultaDte, self).create(vals)
        for r in res:
            r.name = self.env['ir.sequence'].get('consulta.sequence')
        return res

    name = fields.Char(copy=False, readonly=True, default=lambda x: 'Nuevo')
    dCDC=fields.Char(size=44,string='CDC',copy=False)
    xContenDE=fields.Binary(string='XML',copy=False)
    fecha_consulta=fields.Datetime()

    #datos de la respuesta
    dFecProc=fields.Datetime(string='Fecha del procesamiento',copy=False)
    dCodRes=fields.Char(string='Codigo Resultado',copy=False)
    dMsgRes=fields.Char(string='Mje Resultado',copy=False)
    dProtAut=fields.Char(string='Nro de Transaccion',copy=False)
    xContEv=fields.Char(string='Eventos',copy=False)


    def consultar(self):
        self.consultar2()
        # if self.env.company.servidor == 'prueba':
        #     wsdl = 'http://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl?wsdl'
        # else:
        #     wsdl = 'http://sifen.set.gov.py/de/ws/consultas/consulta.wsdl?wsdl'
        # certificado = self.env['firma.digital'].search([
        #     ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
        #     ('estado', '=', 'activo')
        # ], limit=1)
        # if not certificado:
        #     raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        # else:
        #     public_crt = certificado.public_key
        #     private_key = certificado.private_key
        # session = Session()
        # session.cert = (public_crt, private_key)
        # transport = Transport(session=session)
        #
        # client = Client(wsdl, transport=transport)
        #
        # for service in client.wsdl.services.values():
        #     _logger.info("service: %s" % service.name)
        #     for port in service.ports.values():
        #         operations = sorted(port.binding._operations.values(),key=operator.attrgetter('name'))
        #         for operation in operations:
        #             _logger.info("method : %s" % operation.name)
        #             _logger.info("  input : %s" % operation.input.signature())
        #             _logger.info("  output: %s" % operation.output.signature())
        #             _logger.info('---------')
        # request_data = {
        #     'dId': self.id,
        #     'dCDC': self.dCDC,
        # }
        # response = client.service.rEnviConsDe(**request_data)
        # _logger.info('response')
        # _logger.info(response)
        # self.dCodRes = response['dCodRes']
        # if response['dCodRes'] == '0422':
        #     dFecProc=str(response['dFecProc'])
        #     dFecProc = dFecProc[:dFecProc.rfind('-')]
        #     date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%d %H:%M:%S')
        #     self.fecha_consulta=datetime.now()
        #     self.dFecProc=date_time_obj
        #     self.dCodRes=response['dCodRes']
        #     self.dMsgRes=response['dMsgRes']
        #     xml=response['xContenDE']
        #     hasta=xml.find('</rDE>')
        #     if hasta>0:
        #         _logger.info('2')
        #         tam=len('</rDE>')
        #         xml2=xml[:hasta+tam]
        #         data_serialized = xml2.encode(encoding="ascii", errors="xmlcharrefreplace")
        #         archivo=base64.b64encode(data_serialized)
        #         _logger.info('3')
        #         self.sudo().xContenDE=archivo
        #         _logger.info('4')
        #         data_2=xml[hasta+tam:]
        #         _logger.info('data_2: %s' % str(data_2))
        #         dProtAut=data_2[data_2.find('<dProtAut>')+len('<dProtAut>'):data_2.find('</dProtAut>')]
        #         xContEv=data_2[data_2.find('<xContEv>')+len('<xContEv>'):data_2.find('</xContEv>')]
        #         _logger.info('dProtAut: %s' %str(dProtAut))
        #         self.dProtAut=dProtAut
        #         self.xContEv=xContEv

    def consultar2(self):
        if self.env.company.servidor == 'prueba':
            wsdl = 'https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl'
        else:
            wsdl = 'https://sifen.set.gov.py/de/ws/consultas/consulta.wsdl'
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        soap = self.generar_soap_consulta_dte()
        #_logger.info('soap')
        #_logger.info(soap)

        headers = {"Content-Type": "application/soap+xml; charset=UTF-8"}
        certificado2 = (public_crt, private_key)

        response = requests.post(url=wsdl, data=soap, cert=certificado2, headers=headers, verify=False, timeout=180)
        # _logger.info('response')
        #_logger.info(response.text)
        self.parsear_response(response)
        # self.dCodRes = response['dCodRes']
        # if response['dCodRes'] == '0422':
        #     dFecProc = str(response['dFecProc'])
        #     dFecProc = dFecProc[:dFecProc.rfind('-')]
        #     date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%d %H:%M:%S')
        #     self.fecha_consulta = datetime.now()
        #     self.dFecProc = date_time_obj
        #     self.dCodRes = response['dCodRes']
        #     self.dMsgRes = response['dMsgRes']
        #     xml = response['xContenDE']
        #     hasta = xml.find('</rDE>')
        #     if hasta > 0:
        #         _logger.info('2')
        #         tam = len('</rDE>')
        #         xml2 = xml[:hasta + tam]
        #         data_serialized = xml2.encode(encoding="ascii", errors="xmlcharrefreplace")
        #         archivo = base64.b64encode(data_serialized)
        #         _logger.info('3')
        #         self.sudo().xContenDE = archivo
        #         _logger.info('4')
        #         data_2 = xml[hasta + tam:]
        #         _logger.info('data_2: %s' % str(data_2))
        #         dProtAut = data_2[data_2.find('<dProtAut>') + len('<dProtAut>'):data_2.find('</dProtAut>')]
        #         xContEv = data_2[data_2.find('<xContEv>') + len('<xContEv>'):data_2.find('</xContEv>')]
        #         _logger.info('dProtAut: %s' % str(dProtAut))
        #         self.dProtAut = dProtAut
        #         self.xContEv = xContEv

    def parsear_response(self,response):
        # _logger.info('Codigo de retorno set %s' %response.status_code)
        # _logger.info('respueta set %s' %response.text)
            code_300 = False
        # if response.status_code ==200:
            res_tex = response.text
            if res_tex.find('html')<0:
                # self.respuesta = res_tex
                res_tex = res_tex.replace('env:', "").replace('ns2:', "")
                rResEnviLoteDe = res_tex[res_tex.find('rEnviConsDeResponse') - 1:res_tex.rfind('rEnviConsDeResponse') + len('rEnviConsDeResponse') + 1]
                root = ET.fromstring(rResEnviLoteDe)

                for child in root:
                    if child.tag=='dFecProc':
                        dFecProc=child.text
                        dFecProc=dFecProc[:dFecProc.rfind('-')]
                        date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S')
                        self.dFecProc=date_time_obj
                    elif child.tag=='dMsgRes':
                        self.dMsgRes=child.text
                    elif child.tag=='dProtAut':
                        self.dProtAut=child.text
                    elif child.tag=='xContEv':
                        self.xContEv=child.text
                    elif child.tag=='dCodRes':
                        self.dCodRes=child.text
                        if child.text=='0300':
                            code_300=True
                    elif child.tag=='xContenDE':
                        xml = child.text
                        hasta = xml.find('</rDE>')

                        if hasta > 0:
                            #_logger.info('2')
                            tam = len('</rDE>')
                            # xml2 = xml[:hasta + tam]
                            # data_serialized = xml2.encode(encoding="ascii", errors="xmlcharrefreplace")
                            # archivo = base64.b64encode(data_serialized)
                            # _logger.info('3')
                            # self.sudo().xContenDE = archivo
                            #_logger.info('4')
                            data_2 = xml[hasta + tam:]
                            #_logger.info('data_2: %s' % str(data_2))
                            dProtAut = data_2[data_2.find('<dProtAut>') + len('<dProtAut>'):data_2.find('</dProtAut>')]
                            xContEv = data_2[data_2.find('<xContEv>') + len('<xContEv>'):data_2.find('</xContEv>')]
                            #_logger.info('dProtAut: %s' % str(dProtAut))
                            self.dProtAut = dProtAut
                            self.xContEv = xContEv
                            cancel=xContEv.find('rGeVeCan')
                            factura = self.env['account.move'].search([('cdc','=',self.dCDC)])
                            if factura:
                                if cancel>0:
                                    if factura.estado_de !='cancelado':
                                        factura.estado_de='cancelado'
                                else:
                                    if factura.estado_de != 'aprobado':
                                        factura.estado_de='aprobado'
                        # if code_300:
                #     self.state='enviado'
        # #     else:
        #         raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde %s' % response)
        # return code_300

    def generar_soap_consulta_dte(self):
        header = '<?xml version="1.0" encoding="UTF-8"?>' \
                 '<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">' \
                 '<env:Body>' \
                 '<ns0:rEnviConsDeRequest xmlns:ns0="http://ekuatia.set.gov.py/sifen/xsd">'
        id = '<ns0:dId>' + str(self.id) + '</ns0:dId>'
        cdc = '<ns0:dCDC>' + str(self.dCDC) + '</ns0:dCDC>'
        footer = '</ns0:rEnviConsDeRequest>' \
                 '</env:Body>' \
                 '</env:Envelope>'
        soap = header + id  +cdc + footer
        _logger.info('------soap-------')
        _logger.info(soap)
        _logger.info('------fin soap------')
        return soap
