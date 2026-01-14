from odoo import http
from odoo.http import request


class AntuxDataHubController(http.Controller):

    @http.route('/antux_datahub/ips/mensual/<int:batch_id>', type='http', auth='user')
    def ips_import(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        stream, filename = batch.generate_ips_import_excel()
        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )


    @http.route('/antux_datahub/ips/anual/<int:batch_id>', type='http', auth='user')
    def ips_anual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        stream, filename = batch.generate_ips_anual_excel()
        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )