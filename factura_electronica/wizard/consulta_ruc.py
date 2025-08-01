# -*- coding: utf-8 -*-
import operator

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError
from requests import Session
from datetime import datetime
import lxml.etree
import logging

_logger = logging.getLogger(__name__)
try:
    from zeep import Client
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
except (ImportError, IOError) as err:
    _logger.debug(err)


class ConsultaRuc(models.TransientModel):
    _name = 'consulta.ruc'

    ruc = fields.Char()

    def procesar(self):
        ruc = self.ruc
        today = fields.Date.today()
        # certificado=self.env['l10n.es.aeat.certificate'].search([
        #     ('company_id', '=', self.env.company.id),
        #     ('state', '=', 'active')
        certificado = self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id), ('user_ids', '=', self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        if ruc.find('-') >= 0:
            ruc = ruc[:ruc.find('-')]
        try:
            int_ruc = int(ruc)
        except:
            raise ValidationError('El RUC no debe tener letras')
        request_data = {
            'dId': self.id,
            'dRUCCons': ruc,
        }
        _logger.info('----request data----')
        _logger.info(request_data)
        if self.env.company.servidor == 'prueba':
            wsdl = 'http://sifen-test.set.gov.py/de/ws/consultas/consulta-ruc.wsdl?wsdl'
        else:
            wsdl = 'http://sifen.set.gov.py/de/ws/consultas/consulta-ruc.wsdl?wsdl'
        session = Session()
        session.cert = (public_crt, private_key)
        transport = Transport(session=session)

        client = Client(wsdl, transport=transport)

        for service in client.wsdl.services.values():
            _logger.info("service: %s" % service.name)
            for port in service.ports.values():
                operations = sorted(
                    port.binding._operations.values(),
                    key=operator.attrgetter('name'))
                for operation in operations:
                    _logger.info("method : %s" % operation.name)
                    _logger.info("  input : %s" % operation.input.signature())
                    _logger.info("  output: %s" % operation.output.signature())
                    _logger.info('---------')
        metodo = client.get_type('ns0:tRuc')(ruc)
        metodo1 = client.get_type('ns0:dIdType')(self.id)
        _logger.info('metodo %s' % str(metodo))
        _logger.info('metodo1 %s' % str(metodo1))
        fecha = datetime.now()
        result = client.service.rEnviConsRUC(metodo1, metodo)
        _logger.info('Response')
        _logger.info(result)
        mje = result
        if result['dCodRes'] == '0502':
            mje = 'Ruc Consultado: %s' % result['xContRUC']['dRUCCons']
            mje += '\n'
            mje += 'Razon Social: %s' % result['xContRUC']['dRazCons']
            mje += '\n'
            mje += 'Estado: %s' % result['xContRUC']['dDesEstCons']

            if result['xContRUC']['dRUCFactElec'] == 'S':
                mje += 'Facturador Electronico: SI'
            else:
                mje += 'Facturador Electronico: NO'
            mje += '\n'
            mje += 'Fecha de Consulta: %s' % str(fecha)
        elif result['dCodRes'] == '0500':
            mje = result['dMsgRes']

        raise ValidationError(mje)

