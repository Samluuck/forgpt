# -*- coding: utf-8 -*-
# from odoo import http


# class HrReciboAguinaldo(http.Controller):
#     @http.route('/hr_recibo_aguinaldo/hr_recibo_aguinaldo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_recibo_aguinaldo/hr_recibo_aguinaldo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_recibo_aguinaldo.listing', {
#             'root': '/hr_recibo_aguinaldo/hr_recibo_aguinaldo',
#             'objects': http.request.env['hr_recibo_aguinaldo.hr_recibo_aguinaldo'].search([]),
#         })

#     @http.route('/hr_recibo_aguinaldo/hr_recibo_aguinaldo/objects/<model("hr_recibo_aguinaldo.hr_recibo_aguinaldo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_recibo_aguinaldo.object', {
#             'object': obj
#         })
