# -*- coding: utf-8 -*-
# from odoo import http


# class Despachos(http.Controller):
#     @http.route('/despachos/despachos/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/despachos/despachos/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('despachos.listing', {
#             'root': '/despachos/despachos',
#             'objects': http.request.env['despachos.despachos'].search([]),
#         })

#     @http.route('/despachos/despachos/objects/<model("despachos.despachos"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('despachos.object', {
#             'object': obj
#         })
