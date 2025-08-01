# -*- coding: utf-8 -*-



from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config
from odoo import release
import contextlib
import os
import tempfile
import base64
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import OpenSSL.crypto
except (ImportError, IOError) as err:
    _logger.debug(err)

if tuple(map(int, OpenSSL.__version__.split('.'))) < (0, 15):
    _logger.warning(
        'OpenSSL version is not supported. Upgrade to 0.15 or greater.')


@contextlib.contextmanager
def pfx_to_pem(file, pfx_password, directory=None):
    _logger.warning('file-> %s' % file)
    _logger.warning('pfx_password-> %s' % pfx_password)
    _logger.warning('directory-> %s' % directory)
    with tempfile.NamedTemporaryFile(
            prefix='private_', suffix='.pem', delete=False,
            dir=directory) as t_pem:
        f_pem = open(t_pem.name, 'wb')
        p12 = OpenSSL.crypto.load_pkcs12(file,pfx_password)
        _logger.info("PASAMOS %s" %p12)
        f_pem.write(OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, p12.get_privatekey()))
        f_pem.close()
        yield t_pem.name


@contextlib.contextmanager
def pfx_to_crt(file, pfx_password, firma,directory=None):
    with tempfile.NamedTemporaryFile(
            prefix='public_', suffix='.crt', delete=False,
            dir=directory) as t_crt:
        f_crt = open(t_crt.name, 'wb')
        p12 = OpenSSL.crypto.load_pkcs12(file, pfx_password)
        cert=p12.get_certificate()
        f_crt.write(OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM, cert))
        firma.date_start = (datetime.strptime(cert.get_notBefore().decode("utf-8"), '%Y%m%d%H%M%SZ'))
        firma.date_end = (datetime.strptime(cert.get_notAfter().decode("utf-8"), '%Y%m%d%H%M%SZ'))
        f_crt.close()
        yield t_crt.name


class L10nEsAeatCertificatePassword(models.TransientModel):
    _name = 'certificate.pass'

    password = fields.Char(string="Password", required=True)
    firma_digital_id=fields.Many2one('firma.digital')

    # este decorador ya no es valido para la version odoo 15
    def procesar(self):
        if self.password:
            record = self.env['firma.digital'].browse(
                self.env.context.get('active_id'))
            directory = os.path.join(
                os.path.abspath(config['data_dir']), 'certificates',
                release.series, self.env.cr.dbname, record.folder)
            # file = base64.decodestring(record.file)
            file = base64.decodebytes(record.file)
            if tuple(map(int, OpenSSL.__version__.split('.'))) < (0, 15):
                raise exceptions.Warning(
                    _('OpenSSL version is not supported. Upgrade to 0.15 '
                      'or greater.'))
            try:
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                with pfx_to_pem(file, self.password, directory) as private_key:
                    record.private_key = private_key
                with pfx_to_crt(file, self.password,self.firma_digital_id, directory) as public_key:
                    record.public_key = public_key
            except Exception as e:
                if e.args:
                    args = list(e.args)
                raise ValidationError(args[-1])
            self.firma_digital_id.estado='activo'

    def procesar2(self):

        if self.password:
            self.firma_digital_id.password=self.password
            self.firma_digital_id.activar()



